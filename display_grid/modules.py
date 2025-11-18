"""This module provides a component-based architecture for building applications.

The core class is `Module`, which represents a rectangular region of the screen
with its own drawing, event handling, and update logic. Applications are built
by composing Modules and Sub-Modules. Several pre-built modules for common UI
elements like buttons, text input, and FPS meters are also included.
"""
import time
import typing
import io
import contextlib

import numpy as np
import pygame as pg
import urwid

import display_grid as dg

M = typing.TypeVar("M", bound="Module")

class Module:
    """A hierarchical component for managing a region of a grid.
    
    Modules provide a layer of abstraction over Grid objects. They can be nested
    to create complex UIs. A module manages its own sub-region of a parent grid,
    handles its own drawing and event logic, and can contain child modules.
    
    Event propagation flows from parent to child. Update ticks and drawing calls
    also propagate down the hierarchy.
    
    Attributes:
        parent (Module | None): The parent module, or None if this is a root module.
        grid (dg.Grid): The Grid or SubGrid this module draws to.
        submodules (list[Module]): A list of child modules.
        paused (bool): If True, the module is inactive (ignores events, drawing,
            and ticks).
        shape (tuple[int, int]): The (rows, cols) shape of the module's grid.
        box (tuple[int, int, int, int]): The (i0, j0, i1, j1) bounding box of
            this module's grid within its parent's grid.
    """
    
    def __init__(
        self, 
        parent: M | None = None, 
        box: tuple[int, int, int, int] | None = None, 
        grid: dg.Grid | None = None,
    ) -> None:
        """Constructs a Module.

        Args:
            parent: The parent Module. If provided, this module becomes a child
                of the parent and uses a SubGrid of the parent's grid.
            box: A tuple (i0, j0, i1, j1) for the module's bounding box within
                the parent's grid. Ignored if `parent` is None. Negative
                coordinates are relative to the parent's far edge.
            grid: The Grid to draw to. Ignored if `parent` is not None.
        """

        self.parent = parent
        if parent:
            
            if box is None:
                box = 0, 0, *parent.shape
            self.grid = dg.SubGrid(parent.grid, *box)
            parent.submodules.append(self)
        else:
            if box is None:
                box = 0, 0, *grid.shape
            self.grid = dg.SubGrid(grid, *box)
        
        self.submodules: list[M] = []
        self.paused = False
        self.shape = self.grid.shape
        bound = self.parent.shape if parent else self.shape
        self.box = box[0] % bound[0], box[1] % bound[1], box[2] % bound[0], box[3] % bound[1]

    def start(self) -> None:
        """Activates the module, allowing it to be drawn and updated."""
        self.paused = False

    def stop(self) -> None:
        """Deactivates the module. It will not be drawn or updated."""
        self.paused = True

    def draw(self) -> None:
        """Draws this module and its submodules to the grid.
        
        The module's own `_draw` method is called first, followed by the `draw`
        method of each of its submodules.
        """
        if not self.paused:
            self._draw()
            for module in reversed(self.submodules):
                module.draw()
            
    def _draw(self) -> None:
        """The specific drawing logic for this module. Should be overridden."""
        pass

    def tick(self) -> None:
        """Updates this module and its submodules.
        
        The `tick` method of each submodule is called first, followed by this
        module's own `_tick` method.
        """
        if not self.paused:
            for module in self.submodules:
                module.tick()
            self._tick()
            
    def _tick(self) -> None:
        """The specific update logic for this module. Should be overridden."""
        pass

    def handle_event(self, event: dg.Event) -> bool:
        """Handles a user input event, propagating it to submodules first.

        Args:
            event: The `dg.Event` to handle.

        Returns:
            True if the event was handled by this module or one of its
            submodules, False otherwise.
        """
        if self.paused:
            return False
        for module in self.submodules:
            if isinstance(event, dg.MouseEvent):
                i, j = event.pos
                i0, j0, i1, j1 = module.box
                if i0 <= i < i1 and j0 <= j < j1 and module.handle_event(dg.MouseEvent(event.button, event.state, (i - i0, j - j0), event.mod)):
                    return True
            elif isinstance(event, dg.KeyEvent):
                if module.handle_event(event):
                    return True
        return self._handle_event(event)
    
    def _handle_event(self, event: dg.Event) -> bool:
        """The specific event handling logic for this module. Should be overridden.

        Args:
            event: The `dg.Event` to handle.

        Returns:
            True if the event was handled, False otherwise.
        """
        return False

class MainModule(Module):
    """The root module for an application.
    
    This module initializes the display backend (terminal or Pygame) and serves
    as the main entry point for the application's lifecycle (tick, draw, events).
    It can also enforce a specific window size.
    """
    def __init__(
        self, 
        shape: tuple[int, int] = (24, 80), 
        enforce_shape: bool = True, 
        mode: str = typing.Literal["terminal", "pygame"],
    ) -> None:
        """Constructs the MainModule.

        Args:
            shape: The desired (rows, cols) shape of the grid.
            enforce_shape: If True, displays a warning if the window size does
                not match `shape` and pauses updates.
            mode: The backend to use, either "terminal" or "pygame".
        """
        super().__init__(
            grid=dg.Grid(
                np.zeros((*shape, 2, 3), dtype=np.uint8), 
                np.zeros(shape, dtype=np.int32),
                np.zeros(shape, dtype=np.uint8),
            ),
        )
        self.mode = mode
        self.enforce_shape = enforce_shape
        self.printed = io.StringIO()
    
    def _draw(self) -> None:
        """Draws the grid, or a warning if the window shape is incorrect."""
        real_shape = self.grid.get_real_shape()
        if self.enforce_shape and real_shape != self.shape:
            backup_colors = self.grid.colors.copy()
            backup_chars = self.grid.chars.copy()
            backup_attrs = self.grid.attrs.copy()

            self.grid.clear()
            self.grid.chars[:] = ord("█")
            self.grid.chars[1:-1, 2:-2] = ord(" ")
            
            self.grid.print(f"Please ensure the window size is {self.shape[0]}x{self.shape[1]}.", (2, 4), (255, 255, 0), (0, 0, 0))
            self.grid.print(f"The current window size is {real_shape[0]}x{real_shape[1]}.", (3, 4), (255, 255, 0), (0, 0, 0))
            self.grid.draw()

            self.grid.colors[:] = backup_colors
            self.grid.chars[:] = backup_chars
            self.grid.attrs[:] = backup_attrs
        else:
            self.grid.draw()
            
    def _tick(self) -> None:
        """Polls for events if the window shape is correct."""
        if not self.enforce_shape or self.grid.get_real_shape() == self.shape:
            for event in self.grid.events():
                self.handle_event(event)
        else:
            self.grid.events()

    def __enter__(self) -> 'MainModule':
        """Initializes the display backend when entering a `with` block."""
        if self.mode == "terminal":
            self.printed = contextlib.redirect_stdout(self.printed).__enter__()
            scr = urwid.display.raw.Screen()
            scr.start()
            scr.set_input_timeouts(max_wait=0)
            scr.set_mouse_tracking()
            self.grid = dg.TermGrid(scr, self.shape)

            
        elif self.mode == "pygame":
            pg.init()
            self.grid = dg.PygameGrid(pg.display.set_mode(dg.PygameGrid.get_surf_shape(self.shape)))
                
        return self

    def __exit__(
        self, 
        exc_type: typing.Optional[type[BaseException]], 
        exc_value: typing.Optional[BaseException], 
        traceback: typing.Optional[typing.Any],
    ) -> None:
        """Cleans up the display backend when exiting a `with` block."""
        if self.mode == "terminal":
            self.grid.scr.stop()
        elif self.mode == "pygame":
            pg.quit()

class ArrayDrawModule(Module):
    """A module for displaying a NumPy array of RGB data as colored blocks."""
    def __init__(self, parent: Module, box: tuple[int, int, int, int] | None = None, res: int = 1) -> None:
        """Constructs an ArrayDrawModule.

        Args:
            parent: The parent module.
            box: The bounding box within the parent.
            res: An integer scaling factor for the array.
        """
        super().__init__(parent, box)
        self.res = res
        
    def update(self, arr: np.ndarray[np.uint8]) -> None:
        """Updates the module's display with a new array.

        The top half of each character cell gets its color from one row of the
        array, and the bottom half gets its color from the next row.

        Args:
            arr: A NumPy array of shape (height, width, 3) with RGB data.
        """
        arr = np.tile(arr, (self.res, self.res))
        self.grid.chars[:] = ord(dg.BLOCKS[9]) # "▀" character
        self.grid.fg[:] = arr[::2, :, :]
        self.grid.bg[:] = arr[1::2, :, :]

class BarModule(Module):
    """A module for drawing a single horizontal or vertical bar."""
    def __init__(
        self,
        parent: Module,
        box: tuple[int, int, int, int] | None = None,
        direction: int = 0, # 0=+i, 1=+j, 2=-i, 3=-j
    ) -> None:
        """Constructs a BarModule.

        Args:
            parent: The parent module.
            box: The bounding box within the parent.
            direction: The orientation of the bar (0: down, 1: right, 2: up, 3: left).
        """
        super().__init__(parent, box)
        horz, inv = direction % 2, direction // 2

        self.blocks = [dg.BLOCKS, dg.HORZ_BLOCKS][horz][:-1][::2 * (inv != horz) - 1]
        fg, bg = (self.grid.fg, self.grid.bg)[::2 * (inv == horz) - 1]
        self.fg, self.bg, self.chars, self.attrs = [np.moveaxis(a, horz, 0)[::1 - 2 * inv] for a in [fg, bg, self.grid.chars, self.grid.attrs]]

        self.length = self.box[2 + horz] - self.box[horz]
        self.data = np.zeros((self.length * 8, 3), dtype=np.uint8)
        self.nonempty = np.zeros(self.length, dtype=bool)

    def update(self, p0: float, p1: float, color: tuple[int, int, int]) -> None:
        """Sets a segment of the bar to a specific color.

        Args:
            p0: The starting position along the bar's length.
            p1: The ending position along the bar's length.
            color: The (r, g, b) color for the segment.
        """
        p0, p1 = np.clip([min(p0, p1), max(p0, p1)], 0, self.length)
        self.data[int(p0 * 8): int(p1 * 8)] = color
        self.nonempty[int(p0): int(np.ceil(p1))] = True
    
    def reset(self) -> None:
        """Clears all data from the bar."""
        self.data[:] = 0
        self.nonempty[:] = False

    def _draw(self) -> None:
        """Draws the bar to the grid using sub-character blocks."""
        self.fg[self.nonempty] = self.data[7::8, None][self.nonempty]
        self.bg[self.nonempty] = self.data[::8, None][self.nonempty]
        self.chars[self.nonempty] = np.array([ord(b) for b in self.blocks])[np.argmax(np.all(self.data.reshape(-1, 8, 3) == self.data[7::8, None], axis=2), axis=1)][self.nonempty, None]
        self.attrs[self.nonempty] = dg.TA_NONE
        
class ButtonTrigger(Module):
    """A clickable, invisible module that triggers functions on mouse events."""
    def __init__(
        self,
        parent: Module,
        box: tuple[int, int, int, int] | None = None,
        button: int = 0,
        mod: int = dg.KM_NONE,
        down_fn: typing.Callable[[], None] = lambda: None,
        up_fn: typing.Callable[[], None] = lambda: None,
    ) -> None:
        """Constructs a ButtonTrigger.

        Args:
            parent: The parent module.
            box: The bounding box for the clickable area.
            button: The mouse button to react to.
            mod: The required keyboard modifier mask.
            down_fn: The function to call on mouse button down.
            up_fn: The function to call on mouse button up.
        """
        super().__init__(parent, box)
        self.down_fn = down_fn
        self.up_fn = up_fn
        self.button = button
        self.mod = mod
    
    def _handle_event(self, event: dg.Event) -> bool:
        """Handles mouse events and triggers the appropriate function."""
        if isinstance(event, dg.MouseEvent) and event.button == self.button and event.mod == self.mod:
            if event.state:
                self.down_fn()
            else:
                self.up_fn()
            return True
        return False
    
class KeyTrigger(Module):
    """An invisible module that triggers a function on a specific key press."""
    def __init__(
        self,
        parent: Module,
        box: tuple[int, int, int, int] | None = None,
        key: str = " ",
        mod: int = dg.KM_NONE,
        fn: typing.Callable[[], None] = lambda: None,
    ) -> None:
        """Constructs a KeyTrigger.

        Args:
            parent: The parent module.
            box: The bounding box (not used for key triggers, but part of the API).
            key: The key to react to (e.g., "a", "KEY_ENTER").
            mod: The required keyboard modifier mask.
            fn: The function to call when the key is pressed.
        """
        super().__init__(parent, box)
        self.fn = fn
        self.key = key
        self.mod = mod
    
    def _handle_event(self, event: dg.Event) -> bool:
        """Handles key events and triggers the function if it matches."""
        if isinstance(event, dg.KeyEvent) and event.key == self.key and event.mod == self.mod:
            self.fn()
            return True
        return False
    
class TextInputModule(Module):
    """A single-line text input field.
    
    Handles basic text entry, cursor movement, and backspace.
    """
    def __init__(
        self, 
        parent: Module,
        box: tuple[int, int, int, int] | None = None,
        start_text: str = "", 
        empty_text: str = "",
        fg_color: tuple[int, int, int] = [255, 255, 255],
        bg_color: tuple[int, int, int] = [0, 0, 0],
        empty_color: tuple[int, int, int] = [127, 127, 127],
    ) -> None:
        """Constructs a TextInputModule.

        Args:
            parent: The parent module.
            box: The bounding box for the text field.
            start_text: The initial text in the field.
            empty_text: Placeholder text to display when the field is empty.
            fg_color: The color of the text.
            bg_color: The background color of the field.
            empty_color: The color of the placeholder text.
        """
        super().__init__(parent, box)
        self.text = list(start_text)
        self.scroll_pos = max(0, len(start_text) - self.shape[1])
        self.cursor_pos = len(start_text)
        self.empty_text = empty_text
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.empty_color = empty_color

    def _draw(self) -> None:
        """Draws the text field, cursor, and placeholder text."""
        self.grid.fill(" ", self.bg_color, self.bg_color)
        if self.text:
            text = "".join(self.text[self.scroll_pos:self.scroll_pos + self.shape[1]])
            if self.scroll_pos > 0:
                text = "<" + text[1:]
            if len(self.text) > self.shape[1] + self.scroll_pos:
                text = text[:-1] + ">"
            
            self.grid.print(text, (0, 0), self.fg_color, self.bg_color)
            self.grid.fg[0, self.cursor_pos - self.scroll_pos] = self.bg_color
            self.grid.bg[0, self.cursor_pos - self.scroll_pos] = self.fg_color

        else:
            self.grid.print(self.empty_text, (0, 0), self.empty_color, self.bg_color)
        
    def _handle_event(self, event: dg.Event) -> bool:
        """Handles key and mouse events for text input and cursor control."""
        if isinstance(event, dg.MouseEvent):
            self.cursor_pos = event.pos[1] + self.scroll_pos
            return True
        elif isinstance(event, dg.KeyEvent):
            if event.key == "KEY_BACKSPACE":
                if self.cursor_pos > 0:
                    self.text.pop(self.cursor_pos - 1)
                    self.cursor_pos -= 1
                    if self.cursor_pos < self.scroll_pos:
                        self.scroll_pos = max(0, self.scroll_pos - 1)
                return True
            elif event.key == "KEY_LEFT":
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                    if self.cursor_pos < self.scroll_pos:
                        self.scroll_pos = max(0, self.scroll_pos - 1)
                return True
            elif event.key == "KEY_RIGHT":
                if self.cursor_pos < len(self.text):
                    self.cursor_pos += 1
                    if self.cursor_pos >= self.shape[1] + self.scroll_pos:
                        self.scroll_pos += 1
                return True
            elif len(event.key) == 1 and event.key.isprintable():
                self.text.insert(self.cursor_pos, event.key)
                self.cursor_pos += 1
                if self.cursor_pos >= self.shape[1] + self.scroll_pos:
                    self.scroll_pos += 1
                return True
            return False

    def __str__(self) -> str:
        """Returns the current text content of the module."""
        return "".join(self.text)

class FPSMeter(Module):
    """A module that displays the current frames per second."""
    def __init__(self, parent: Module, box: tuple[int, int, int, int] | None = None) -> None:
        """Constructs an FPSMeter.

        Args:
            parent: The parent module.
            box: The bounding box for the meter. Recommended shape is 1x8.
        """
        super().__init__(parent, box)
        self.avg = 60
        self.last_time = time.time()

    def _tick(self) -> None:
        """Calculates the FPS based on the time since the last tick."""
        cur_time = time.time()
        fps = 1 / (cur_time - self.last_time)
        self.last_time = cur_time
        self.avg = 0.9 * self.avg + 0.1 * fps

    def _draw(self) -> None:
        """Displays the calculated FPS."""
        if self.shape[0] == 1:
            self.grid.print("FPS:" + str(int(self.avg)).rjust(self.shape[1] - 4))
        else:
            self.grid.print("FPS:")
            self.grid.print(str(int(self.avg)).ljust(self.shape[1]), (1, 0))
        
class BorderModule(Module):
    """A module that draws a border around its perimeter."""
    def __init__(self, parent: Module, box: tuple[int, int, int, int] | None = None, depth: int = 1.0) -> None:
        """Constructs a BorderModule.

        Args:
            parent: The parent module.
            box: The bounding box for the border.
            depth: The thickness of the border in characters.
        """
        super().__init__(parent, box)
        self.depth = depth
        self.inner_box = int(np.ceil(depth / 2)), depth, self.shape[0] - int(np.ceil(depth / 2)), self.shape[1] - depth

    def _draw(self) -> None:
        """Draws the border using block characters."""
        self.grid.chars[:self.depth // 2, :] = ord("█")
        self.grid.chars[-(self.depth // 2):, :] = ord("█")
        
        if self.depth % 2 == 1:
            self.grid.chars[self.depth // 2, :] = ord("▀")
            self.grid.chars[-(self.depth // 2) - 1, :] = ord("▄") 

        self.grid.chars[:, :self.depth] = ord("█")
        self.grid.chars[:, -self.depth:] = ord("█")

class TabModule(Module):
    """A container module that manages a list of other modules as tabs.
    
    Only one tab is active (visible and interactive) at a time.
    """
    def __init__(
        self, 
        parent: Module, 
        box: tuple[int, int, int, int] | None = None,
        tabs: list[Module] | None = None,
    ) -> None:
        """Constructs a TabModule.

        Args:
            parent: The parent module.
            box: The bounding box for the tab content area.
            tabs: A list of modules to be used as tabs.
        """
        super().__init__(parent, box)
        self.tabs = []
        self._index = None
        if tabs:
            self.tabs = tabs
            for tab in self.tabs:
                tab.stop()
            self.index = 0
            
    @property
    def index(self) -> int:
        """The index of the currently active tab."""
        return self._index
    
    @index.setter
    def index(self, value: int | None) -> None:
        """Sets the active tab by its index."""
        if self._index is not None:
            self.tabs[self._index].stop()
        self._index = value
        if self._index is not None:
            self.tabs[self._index].start()

    @property
    def tab(self) -> Module | None:
        """The currently active tab module."""
        return self.tabs[self._index]
    
    @tab.setter
    def tab(self, value: Module | None) -> None:
        """Sets the active tab by its module instance."""
        if value is None:
            self.index = None
        else:
            self.index = self.tabs.index(value)

if __name__ == "__main__":
    import PIL.Image as Image
    import time

    import pygame as pg

    pg.init()

    images = []
    for i in range(10):
        img = Image.open(f"temp/{i}.png").convert("RGB")
        img = img.resize((64, 64))
        images.append(np.array(img).reshape(64, 64, 3))
    
    clock = pg.time.Clock()
    with MainModule((34, 68), enforce_shape=True, mode="terminal") as main_module:
        # sb_module = ScoreboardModule(main_module)
        border_module = BorderModule(main_module, None, 2)
        arr_module = ArrayDrawModule(border_module, border_module.inner_box)
        fps_module = FPSMeter(main_module, (0, 0, 1, 8))
        while True:
            for i in range(10):
                arr_module.update(images[i])
                clock.tick(60)
                
                main_module.tick()
                main_module.draw()
            
            
                
    # curses.wrapper(main)

    # scr = pg.display.set_mode(dg.PygameGrid.get_surf_shape((34, 68)))
    # main(scr)