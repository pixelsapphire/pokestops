import announcements
import customtkinter as ctk
import gtfs
import log
import ref
import sys
import util
from abc import ABC, abstractmethod
from database import Database
from player import Player
from tkinter import TclError
from typing import Any, Callable, override
from uibuilder import UIBuilder
from PIL import Image, ImageTk


class styles:
    side_buttons: dict[str, dict[str, Any]] = {
        'appearance': {'width': 192, 'height': 48, 'anchor': ctk.W, 'border_spacing': 8, 'corner_radius': 0,
                       'fg_color': '#282828', 'hover_color': '#383838', 'font': ('SF Display', 16), 'state': ctk.DISABLED},
        'layout': {'fill': ctk.X, 'pady': 4}
    }
    update_buttons: dict[str, dict[str, Any]] = {
        'appearance': {'height': 48, 'corner_radius': 0, 'font': ('SF Display', 16)},
        'layout': {'sticky': ctk.EW + ctk.S, 'padx': 32, 'pady': 8}
    }
    update_labels: dict[str, dict[str, Any]] = {
        'appearance': {'text_color': '#777777', 'font': ('SF Display', 12)},
        'layout': {'sticky': ctk.N}
    }
    tiled_buttons: dict[str, dict[str, Any]] = {
        'appearance': {'compound': ctk.TOP, 'border_spacing': 8, 'corner_radius': 0,
                       'fg_color': '#282828', 'hover_color': '#383838', 'font': ('SF Display', 16)},
        'layout': {'side': ctk.LEFT, 'fill': ctk.X, 'padx': 8}
    }


class icons:
    database: Image = util.image_from_svg(ref.asset_icon_database, 128, 128)
    manufacturing: Image = util.image_from_svg(ref.asset_icon_manufacturing, 128, 128)
    group: Image = util.image_from_svg(ref.asset_icon_group, 128, 128)
    person: Image = util.image_from_svg(ref.asset_icon_person, 128, 128)
    route: Image = util.image_from_svg(ref.asset_icon_route, 128, 128)


class ToolGUI(ctk.CTk):
    LEFT_CLICK: str = '<Button-1>'
    SIZE_24: tuple[int, int] = (24, 24)
    SIZE_96: tuple[int, int] = (96, 96)

    def __init__(self, get_database: Callable[[], Database],
                 update_gtfs: Callable[[Database, UIBuilder], None], update_announcements: Callable[[Database], None],
                 compile_map: Callable[[UIBuilder], None], compile_archive: Callable[[UIBuilder], None],
                 compile_announcements: Callable[[UIBuilder], None], compile_raids: Callable[[UIBuilder], None]):
        super().__init__()
        self.extfn_get_database: Callable[[], Database] = get_database
        self.extfn_update_gtfs: Callable[[Database, UIBuilder], None] = update_gtfs
        self.extfn_update_announcements: Callable[[Database], None] = update_announcements
        self.extfn_compile_map: Callable[[UIBuilder], None] = compile_map
        self.extfn_compile_archive: Callable[[UIBuilder], None] = compile_archive
        self.extfn_compile_announcements: Callable[[UIBuilder], None] = compile_announcements
        self.extfn_compile_raids: Callable[[UIBuilder], None] = compile_raids

        self.database: Database | None = None
        self.page_builder: UIBuilder | None = None

        # noinspection PyTypeChecker
        self.wm_iconphoto(False, ImageTk.PhotoImage(Image.open(ref.asset_img_compass)))
        self.wm_title('Pokestops Tool')
        self.geometry('800x600')

        self.pane_content: ctk.CTkFrame = ctk.CTkFrame(self)
        self.init_content_pane()

        self.content_pane_columns: int = 0
        self.content_pane_rows: int = 0

        self.pane_side_buttons: ctk.CTkFrame = ctk.CTkFrame(self)
        self.img_logo: ctk.CTkLabel = ctk.CTkLabel(self.pane_side_buttons)
        self.btn_updates: ctk.CTkButton = ctk.CTkButton(self.pane_side_buttons, **styles.side_buttons['appearance'])
        self.btn_players: ctk.CTkButton = ctk.CTkButton(self.pane_side_buttons, **styles.side_buttons['appearance'])
        self.btn_compilation: ctk.CTkButton = ctk.CTkButton(self.pane_side_buttons, **styles.side_buttons['appearance'])
        self.btn_raid_tools: ctk.CTkButton = ctk.CTkButton(self.pane_side_buttons, **styles.side_buttons['appearance'])
        self.init_sidebar()

    def init_sidebar(self) -> None:
        self.pane_side_buttons.configure(fg_color='#181818')
        self.pane_side_buttons.pack(side=ctk.LEFT, fill=ctk.Y)

        self.img_logo.configure(text='', image=ctk.CTkImage(Image.open(ref.asset_img_compass), size=ToolGUI.SIZE_96))
        self.img_logo.pack(fill=ctk.X, pady=32)

        self.btn_updates.configure(require_redraw=True, text='Data update', command=UpdatesTab(self).open,
                                   image=ctk.CTkImage(icons.database, size=ToolGUI.SIZE_24))
        self.btn_updates.pack(**styles.side_buttons['layout'])

        self.btn_players.configure(require_redraw=True, text='Players\' data', command=PlayersTab(self).open,
                                   image=ctk.CTkImage(icons.group, size=ToolGUI.SIZE_24))
        self.btn_players.pack(**styles.side_buttons['layout'])

        self.btn_compilation.configure(require_redraw=True, text='Page compilation', command=CompilationTab(self).open,
                                       image=ctk.CTkImage(icons.manufacturing, size=ToolGUI.SIZE_24))
        self.btn_compilation.pack(**styles.side_buttons['layout'])

        self.btn_raid_tools.configure(require_redraw=True, text='Raid tools', command=RaidToolsTab(self).open,
                                      image=ctk.CTkImage(icons.route, size=ToolGUI.SIZE_24))
        self.btn_raid_tools.pack(**styles.side_buttons['layout'])

    def init_content_pane(self) -> None:
        self.pane_content.configure(fg_color='#181818')
        self.pane_content.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True)

        ctk.CTkLabel(self.pane_content,
                     text='Welcome to the Pokestops Tool!\nSelect an option from the sidebar to get started.',
                     text_color='#777777', font=('SF Display', 32)).pack(fill=ctk.BOTH, expand=True)

    def open_errors_dialog(self, title: str, message: str) -> None:
        dialog: ctk.CTkToplevel = ctk.CTkToplevel(self)
        dialog.wm_title(title)
        dialog.wm_transient(self)
        dialog.wm_resizable(False, False)
        dialog.wm_geometry('750x250')
        ctk.CTkLabel(dialog, text=message, height=48).pack(fill=ctk.X)
        txt_errors: ctk.CTkTextbox = ctk.CTkTextbox(dialog, wrap=ctk.NONE)
        txt_errors.insert('0.0', '\n'.join(log.flush_errors()))
        txt_errors.configure(state=ctk.DISABLED)
        txt_errors.pack(fill=ctk.BOTH, expand=True)

    def cmd_load_database(self, *_: Any) -> None:
        for button in [b for b in self.pane_side_buttons.winfo_children() if isinstance(b, ctk.CTkButton)]:
            button.configure(state=ctk.DISABLED)
        self.database = self.extfn_get_database()
        self.page_builder = UIBuilder(database=self.database, lexmap_file=ref.lexmap_polish)
        if log.errors_present():
            self.open_errors_dialog(title='Warning', message='Database loaded with the following warnings:')
        for button in [b for b in self.pane_side_buttons.winfo_children() if isinstance(b, ctk.CTkButton)]:
            button.configure(state=ctk.NORMAL)

    def start(self):
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')
        self.focus_force()
        self.attributes("-zoomed", True) if sys.platform.startswith('linux') else self.state('zoomed')
        self.after(0, self.cmd_load_database)
        self.mainloop()


class ToolGUITab(ABC):
    def __init__(self, master: ToolGUI):
        self.master: ToolGUI = master
        self.content_pane: ctk.CTkFrame = self.master.pane_content

    def prepare_content_pane(self, /, columns: list[int] | None = None, rows: list[int] | None = None) -> None:
        for widget in self.content_pane.winfo_children():
            widget.destroy()
        for c in range(0, self.master.content_pane_columns):
            self.content_pane.columnconfigure(c, weight=0)
        for r in range(0, self.master.content_pane_rows):
            self.content_pane.rowconfigure(r, weight=0)
        if columns:
            for i in range(len(columns)):
                self.content_pane.columnconfigure(i, weight=columns[i])
            self.master.content_pane_columns = max(self.master.content_pane_columns, len(columns))
        if rows:
            for i in range(len(rows)):
                self.content_pane.rowconfigure(i, weight=rows[i])
            self.master.content_pane_rows = max(self.master.content_pane_rows, len(rows))

    @abstractmethod
    def open(self) -> None:
        pass


class UpdatesTab(ToolGUITab):
    def __init__(self, master: ToolGUI):
        super().__init__(master)
        self.txt_update_gtfs: ctk.CTkLabel | None = None
        self.txt_update_announcements: ctk.CTkLabel | None = None

    @override
    def open(self) -> None:
        self.prepare_content_pane(columns=[1, 1], rows=[20, 5, 2, 5, 5, 20])

        btn_update_gtfs: ctk.CTkButton = ctk.CTkButton(self.content_pane, **styles.update_buttons['appearance'])
        btn_update_gtfs.configure(text='Update GTFS data', command=self.cmd_update_gtfs)
        btn_update_gtfs.grid(**styles.update_buttons['layout'], row=1, column=0)

        self.txt_update_gtfs = ctk.CTkLabel(self.content_pane)
        self.txt_update_gtfs.configure(**styles.update_labels['appearance'],
                                       text=f'Last updated: {gtfs.get_last_update_time()}')
        self.txt_update_gtfs.grid(**styles.update_labels['layout'], row=2, column=0)

        btn_update_announcements: ctk.CTkButton = ctk.CTkButton(self.content_pane, **styles.update_buttons['appearance'])
        btn_update_announcements.configure(text='Update announcements', command=self.cmd_update_announcements)
        btn_update_announcements.grid(**styles.update_buttons['layout'], row=1, column=1)

        self.txt_update_announcements = ctk.CTkLabel(self.content_pane)
        self.txt_update_announcements.configure(**styles.update_labels['appearance'],
                                                text=f'Last updated: {announcements.get_last_update_time()}')
        self.txt_update_announcements.grid(**styles.update_labels['layout'], row=2, column=1)

        btn_update_both: ctk.CTkButton = ctk.CTkButton(self.content_pane, **styles.update_buttons['appearance'])
        btn_update_both.configure(text='Update both', command=self.cmd_update_gtfs_and_announcements)
        btn_update_both.grid(**styles.update_buttons['layout'], row=3, column=0, columnspan=2)

        btn_refresh: ctk.CTkButton = ctk.CTkButton(self.content_pane, **styles.update_buttons['appearance'])
        btn_refresh.configure(text='Refresh', command=self.master.cmd_load_database)
        btn_refresh.grid(**styles.update_buttons['layout'], row=4, column=0, columnspan=2)

    def cmd_update_gtfs(self) -> None:
        self.master.extfn_update_gtfs(self.master.database, self.master.page_builder)
        self.master.database.make_update_report()
        try:
            self.txt_update_gtfs.configure(text=f'Last updated: {gtfs.get_last_update_time()}')
        except TclError:
            pass

    def cmd_update_announcements(self) -> None:
        self.master.extfn_update_announcements(self.master.database)
        self.master.database.make_update_report()
        try:
            self.txt_update_announcements.configure(text=f'Last updated: {announcements.get_last_update_time()}')
        except TclError:
            pass

    def cmd_update_gtfs_and_announcements(self) -> None:
        self.master.extfn_update_gtfs(self.master.database, self.master.page_builder)
        self.master.extfn_update_announcements(self.master.database)
        self.master.database.make_update_report()
        try:
            self.txt_update_gtfs.configure(text=f'Last updated: {gtfs.get_last_update_time()}')
            self.txt_update_announcements.configure(text=f'Last updated: {announcements.get_last_update_time()}')
        except TclError:
            pass


class PlayersTab(ToolGUITab):
    def __init__(self, master: ToolGUI):
        super().__init__(master)
        self.pane_player_data: ctk.CTkFrame | None = None

    @override
    def open(self) -> None:
        self.prepare_content_pane()

        pane_players: ctk.CTkFrame = ctk.CTkFrame(self.content_pane, fg_color='transparent')
        pane_players.pack(fill=ctk.X, padx=32, pady=32)

        for player in self.master.database.players:
            avatar_image: Image = util.tint_image(icons.person, player.tint_color)
            btn_player: ctk.CTkButton = ctk.CTkButton(pane_players, **styles.tiled_buttons['appearance'])
            btn_player.configure(require_redraw=True, text=player.nickname, command=lambda p=player: self.cmd_select_player(p),
                                 image=ctk.CTkImage(avatar_image, size=ToolGUI.SIZE_96))
            btn_player.pack(**styles.tiled_buttons['layout'])

        self.pane_player_data = ctk.CTkFrame(self.content_pane, fg_color='transparent')
        self.pane_player_data.pack(fill=ctk.BOTH, expand=True, padx=32, pady=32)

    def cmd_select_player(self, player: Player) -> None:
        for widget in self.pane_player_data.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.pane_player_data, text=player.nickname, font=('SF Display', 128)).pack(fill=ctk.X)


class CompilationTab(ToolGUITab):
    @override
    def open(self) -> None:
        self.prepare_content_pane(rows=[1, 1, 1, 1], columns=[1])
        buttons_layout: dict[str, Any] = {**styles.update_buttons['layout'], 'sticky': ctk.EW}

        btn_compile_map: ctk.CTkButton = ctk.CTkButton(self.content_pane, **styles.update_buttons['appearance'])
        btn_compile_map.configure(text='Compile map', command=self.cmd_compile_map)
        btn_compile_map.grid(**buttons_layout, row=0)

        btn_compile_archive: ctk.CTkButton = ctk.CTkButton(self.content_pane, **styles.update_buttons['appearance'])
        btn_compile_archive.configure(text='Compile archive', command=self.cmd_compile_archive)
        btn_compile_archive.grid(**buttons_layout, row=1)

        btn_compile_announcements: ctk.CTkButton = ctk.CTkButton(self.content_pane, **styles.update_buttons['appearance'])
        btn_compile_announcements.configure(text='Compile announcements', command=self.cmd_compile_announcements)
        btn_compile_announcements.grid(**buttons_layout, row=2)

        btn_compile_raids: ctk.CTkButton = ctk.CTkButton(self.content_pane, **styles.update_buttons['appearance'])
        btn_compile_raids.configure(text='Compile raids', command=self.cmd_compile_raids)
        btn_compile_raids.grid(**buttons_layout, row=3)

    def cmd_compile_map(self) -> None:
        self.master.page_builder.compile_data()
        self.master.extfn_compile_map(self.master.page_builder)

    def cmd_compile_archive(self) -> None:
        self.master.page_builder.compile_data()
        self.master.extfn_compile_archive(self.master.page_builder)

    def cmd_compile_announcements(self) -> None:
        self.master.page_builder.compile_data()
        self.master.extfn_compile_announcements(self.master.page_builder)

    def cmd_compile_raids(self) -> None:
        self.master.page_builder.compile_data()
        self.master.extfn_compile_raids(self.master.page_builder)


class RaidToolsTab(ToolGUITab):
    @override
    def open(self) -> None:
        self.prepare_content_pane()
