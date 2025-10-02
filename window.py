# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-02 14:45:20
# @LastEditTime: 2025-10-02 18:06:49
# @FilePath: /DeltaForceScript/window.py
# @Description: 窗口截图工具 - 包含Windows Graphics Capture API支持

# SPDX-License-Identifier: MIT
# Copyright 2024 David Lechner <david@pybricks.com>

"""
This is an example of how to use PyWinRT to capture a screen image from a
command line program.

Run this script as a module ``py -m samples.screen_capture`` and select a
window to capture. If the window is minimized, activate it, otherwise the
capture will time out. The captured image will be saved as
``pywinrt example screen capture.png`` in the current directory.
"""
import contextlib
import os
from threading import Event
from typing import Callable
from winrt.windows.graphics.capture import (
    GraphicsCaptureItem,
    Direct3D11CaptureFramePool,
)
from winrt.windows.graphics.directx import DirectXPixelFormat
from winrt.windows.graphics.directx.direct3d11.interop import (
    create_direct3d11_device_from_dxgi_device,
)
from winrt.windows.graphics.imaging import BitmapEncoder, SoftwareBitmap, BitmapBufferAccessMode
from winrt.windows.storage import CreationCollisionOption, FileAccessMode, StorageFolder
from winrt.windows.ui.windowmanagement import WindowServices

import numpy as np
from PIL import Image

from d3d11 import D3D_DRIVER_TYPE, D3D11_CREATE_DEVICE_FLAG, D3D11CreateDevice

if os.environ.get("MSYSTEM", ""):
    _getfullpathname: Callable[[str], str]
    from nt import _getfullpathname  # type: ignore

    # HACK: MSYS hacks ntpath module to use unix directory separators when the
    # MSYSTEM environment variable is present, so we have to work around that.
    def abspath(path: str) -> str:
        return _getfullpathname(os.path.normpath(path))
else:
    abspath = os.path.abspath

class WindowsCapture():
    def __init__(self):
        selected_item = self.selected_item()
        dxgi, _, context = D3D11CreateDevice(
            DriverType=D3D_DRIVER_TYPE.HARDWARE,
            Flags=D3D11_CREATE_DEVICE_FLAG.BGRA_SUPPORT,
        )
        self.stack = contextlib.ExitStack()
        device = self.stack.enter_context(create_direct3d11_device_from_dxgi_device(dxgi.value))

        self.frame_pool = self.stack.enter_context(
            Direct3D11CaptureFramePool.create_free_threaded(
                device,
                DirectXPixelFormat.R8_G8_B8_A8_UINT_NORMALIZED,
                1,
                selected_item.size,
            )
        )

        self.session = self.stack.enter_context(self.frame_pool.create_capture_session(selected_item))

        self.event = Event()
        token = self.frame_pool.add_frame_arrived(lambda _, __: self.event.set())
        self.stack.callback(self.frame_pool.remove_frame_arrived, token)

    def selected_item(self) -> GraphicsCaptureItem:
        capture_items: list[GraphicsCaptureItem] = []

        for win_id in WindowServices.find_all_top_level_window_ids():
            item = GraphicsCaptureItem.try_create_from_window_id(win_id)

            if item is None:
                continue

            capture_items.append(item)
            print(len(capture_items), item.display_name, sep=". ")

        print()
        selection = input("Select a window to capture: ")
        selected_item = capture_items[int(selection) - 1]
        return selected_item

    def capture(self, timeout: float = 1.0) -> np.ndarray:
        self.session.start_capture()
        if not self.event.wait(timeout):
            print("Timed out waiting for frame - is window minimized?")
            exit(1)

        frame = self.frame_pool.try_get_next_frame()
        assert frame is not None, "This shouldn't happen since we waited for the event."

        self.stack.enter_context(frame)
        bitmap = self.stack.push(
            SoftwareBitmap.create_copy_from_surface_async(frame.surface).get()
        )
        # 获取位图缓冲区
        buffer = bitmap.lock_buffer(BitmapBufferAccessMode.READ)
        plane = buffer.get_plane_description(0)

        # 获取内存引用
        memory_buffer = buffer.create_reference()
        # 转换为字节数组
        import ctypes
        from winrt.windows.storage.streams import IBufferByteAccess
        buffer_byte_access = memory_buffer.query_interface(IBufferByteAccess)
        byte_array = ctypes.POINTER(ctypes.c_byte * memory_buffer.length)()
        buffer_byte_access.buffer(byte_array)
        
        # 转换为 numpy 数组
        image_array = np.frombuffer(
            ctypes.cast(byte_array, ctypes.POINTER(ctypes.c_byte * memory_buffer.length)).contents,
            dtype=np.uint8
        )

        return image_array


def main():
    capturer = WindowsCapture()
    filename = abspath("./pywinrt_example_screen_capture.png")
    if capturer.capture_to_file(filename):
        print(f"Saved capture to {filename}")
    else:
        print("Capture failed")

if __name__ == "__main__":
    main()
