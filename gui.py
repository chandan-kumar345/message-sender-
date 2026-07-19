import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Callable, Optional

# Set CustomTkinter appearance defaults
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class WhatsAppSenderGUI(ctk.CTk):
    """The main GUI application window class for WhatsApp Lead Sender."""
    
    def __init__(self, settings_manager: Any):
        super().__init__()
        
        self.settings = settings_manager
        
        # Configure window settings
        self.title("WhatsApp Lead Dispatcher - Sooftcode")
        self.geometry("1280x820")
        self.minimum_width = 1100
        self.minimum_height = 700
        self.minsize(self.minimum_width, self.minimum_height)
        
        # Controller callbacks mapping
        self.callbacks: Dict[str, Callable] = {}
        
        # UI State variables
        self.active_tab = "dashboard"
        self.selected_file_path = ""
        self.attachment_file_path = ""
        self.leads_data: List[Dict[str, Any]] = []
        self.filtered_leads: List[Dict[str, Any]] = []
        self.current_preview_index = -1
        
        # Scheduling state
        self.is_scheduled = False
        
        # Layout grids
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Setup sidebar (left) and content (right)
        self._setup_sidebar()
        self._setup_content_area()
        
        # Load theme from settings
        self.apply_theme(self.settings.app_theme)
        
        # Bind resize event to auto-adjust columns
        self.bind("<Configure>", self._on_resize)
        
    def set_callback(self, name: str, callback: Callable) -> None:
        """Register controller callback functions."""
        self.callbacks[name] = callback
        
    def apply_theme(self, theme: str) -> None:
        """Applies the theme to CTk and configures the Treeview style mapping."""
        if theme in ["System", "Dark", "Light"]:
            ctk.set_appearance_mode(theme)
            self._update_treeview_styles(theme.lower())

    def _update_treeview_styles(self, mode: str) -> None:
        """Configures the Tkinter ttk.Treeview styles to match dark/light theme."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Set dark/light properties
        if mode == "dark" or (mode == "system" and ctk.get_appearance_mode() == "Dark"):
            bg = "#1e1e1e"
            fg = "#ffffff"
            field_bg = "#1e1e1e"
            head_bg = "#2b2b2b"
            head_fg = "#ffffff"
            select_bg = "#1f6aa5"
            border_color = "#333333"
        else:
            bg = "#ffffff"
            fg = "#000000"
            field_bg = "#ffffff"
            head_bg = "#eaeaea"
            head_fg = "#000000"
            select_bg = "#3a7ebf"
            border_color = "#cccccc"
            
        style.configure("Treeview",
                        background=bg,
                        foreground=fg,
                        fieldbackground=field_bg,
                        rowheight=28,
                        font=("Segoe UI", 9),
                        bordercolor=border_color,
                        borderwidth=1)
                        
        style.configure("Treeview.Heading",
                        background=head_bg,
                        foreground=head_fg,
                        bordercolor=border_color,
                        font=("Segoe UI", 9, "bold"))
                        
        style.map("Treeview",
                  background=[("selected", select_bg)],
                  foreground=[("selected", "#ffffff")])

    def _on_resize(self, event) -> None:
        """Trigger updates on window resizing (safeguard treeview column widths)."""
        pass

    def _setup_sidebar(self) -> None:
        """Creates the left navigation sidebar."""
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)  # Spacer push
        
        # Logo / Brand Title
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SOOFTCODE", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        self.subtitle_label = ctk.CTkLabel(self.sidebar_frame, text="WhatsApp Dispatcher", text_color="#10b981", font=ctk.CTkFont(size=12, weight="bold"))
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        self.separator = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#333333")
        self.separator.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        # Navigation Buttons
        self.nav_btns = {}
        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("campaign", "🚀  Campaign Manager"),
            ("templates", "📝  Template Builder"),
            ("logs", "📋  System Logs"),
            ("settings", "⚙️  Settings")
        ]
        
        for idx, (tab_id, label) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=label,
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                height=40,
                command=lambda tid=tab_id: self.select_tab(tid)
            )
            btn.grid(row=3 + idx, column=0, sticky="ew", padx=15, pady=4)
            self.nav_btns[tab_id] = btn
            
        # Version and Theme Select (Bottom)
        self.theme_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w", font=ctk.CTkFont(size=11))
        self.theme_label.grid(row=8, column=0, padx=20, pady=(10, 2))
        
        self.theme_option = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["System", "Dark", "Light"],
            command=self._on_theme_changed
        )
        self.theme_option.grid(row=9, column=0, padx=20, pady=(2, 15))
        self.theme_option.set(self.settings.app_theme)
        
        self.version_label = ctk.CTkLabel(self.sidebar_frame, text="v1.0.0 Stable", text_color="gray50", font=ctk.CTkFont(size=10))
        self.version_label.grid(row=10, column=0, padx=20, pady=(0, 10))

    def _setup_content_area(self) -> None:
        """Sets up the container for switching content tabs on the right side."""
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)
        
        # Create all subframes
        self.frames: Dict[str, ctk.CTkFrame] = {
            "dashboard": self._create_dashboard_frame(),
            "campaign": self._create_campaign_frame(),
            "templates": self._create_templates_frame(),
            "logs": self._create_logs_frame(),
            "settings": self._create_settings_frame()
        }
        
        # Default start tab
        self.select_tab("dashboard")

    def select_tab(self, tab_id: str) -> None:
        """Switches between right-side tabs and updates styling of sidebar navigation buttons."""
        self.active_tab = tab_id
        
        # Hide all frames and show selected
        for fid, frame in self.frames.items():
            frame.grid_forget()
            
        self.frames[tab_id].grid(row=0, column=0, sticky="nsew")
        
        # Update navigation button states (highlight active tab)
        for btn_id, btn in self.nav_btns.items():
            if btn_id == tab_id:
                btn.configure(fg_color=("#1f6aa5", "#1f6aa5"), text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))
                
        # Trigger dynamic checks when landing on tabs
        if tab_id == "dashboard" and "refresh_dashboard" in self.callbacks:
            self.callbacks["refresh_dashboard"]()
        elif tab_id == "templates" and "refresh_templates" in self.callbacks:
            self.callbacks["refresh_templates"]()
        elif tab_id == "logs" and "refresh_logs" in self.callbacks:
            self.callbacks["refresh_logs"]()

    def _on_theme_changed(self, choice: str) -> None:
        """Triggered when user selects a different appearance theme."""
        self.settings.save(app_theme=choice)
        self.apply_theme(choice)

    # =========================================================================
    # TAB FRAME CREATION METHODS
    # =========================================================================

    def _create_dashboard_frame(self) -> ctk.CTkFrame:
        """Generates the Dashboard layout."""
        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(frame, text="Dashboard Overview", font=ctk.CTkFont(size=22, weight="bold"))
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Cards Subframe
        cards_frame = ctk.CTkFrame(frame, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="new", pady=(0, 20))
        
        # Configure columns (3x2 grid of metrics cards)
        for col in range(3):
            cards_frame.grid_columnconfigure(col, weight=1, minsize=200)
            
        self.dash_cards = {}
        metrics = [
            ("total", "Total Leads", "0", "gray50"),
            ("selected", "Selected Leads", "0", "#3b82f6"),
            ("sent", "Successfully Sent", "0", "#10b981"),
            ("failed", "Failed Deliveries", "0", "#ef4444"),
            ("pending", "Pending Queue", "0", "#eab308"),
            ("success_rate", "Success Rate", "0.0%", "#8b5cf6")
        ]
        
        for idx, (key, label, default, color) in enumerate(metrics):
            row = idx // 3
            col = idx % 3
            
            card = ctk.CTkFrame(cards_frame, corner_radius=10, border_width=1, border_color=("gray80", "gray30"))
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            card.grid_columnconfigure(0, weight=1)
            
            lbl = ctk.CTkLabel(card, text=label, text_color="gray50", font=ctk.CTkFont(size=13, weight="normal"))
            lbl.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
            
            val = ctk.CTkLabel(card, text=default, text_color=color, font=ctk.CTkFont(size=28, weight="bold"))
            val.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")
            
            self.dash_cards[key] = val

        # Analytics / Visual area
        details_frame = ctk.CTkFrame(frame, fg_color="transparent")
        details_frame.grid(row=2, column=0, sticky="nsew", pady=10)
        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_columnconfigure(1, weight=1)
        
        # Left Details Card: App stats details
        left_card = ctk.CTkFrame(details_frame)
        left_card.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="nsew")
        left_card.grid_columnconfigure(0, weight=1)
        
        left_title = ctk.CTkLabel(left_card, text="Campaign Summary Details", font=ctk.CTkFont(size=15, weight="bold"))
        left_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")
        
        self.lbl_summary_desc = ctk.CTkLabel(
            left_card,
            text="No active campaign records loaded.\nImport files in the Campaign Manager to begin.",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_summary_desc.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="w")

        # Right Details Card: Active Template Details
        right_card = ctk.CTkFrame(details_frame)
        right_card.grid(row=0, column=1, padx=(10, 0), pady=10, sticky="nsew")
        right_card.grid_columnconfigure(0, weight=1)
        
        right_title = ctk.CTkLabel(right_card, text="Quick Connection Status", font=ctk.CTkFont(size=15, weight="bold"))
        right_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")
        
        self.lbl_conn_status = ctk.CTkLabel(
            right_card,
            text="Testing API Credentials status...\nConfigure settings under settings panel.",
            justify="left",
            anchor="w",
            text_color="gray50",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_conn_status.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="w")
        
        return frame

    def _create_campaign_frame(self) -> ctk.CTkFrame:
        """Generates the Campaign Manager view (import leads, review, compose templates, send)."""
        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=5)  # Left table
        frame.grid_columnconfigure(1, weight=4)  # Right composer/controls
        frame.grid_rowconfigure(1, weight=1)
        
        # Header controls
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        btn_import = ctk.CTkButton(header_frame, text="📂 Import Leads File", command=self._on_import_leads_click, width=140)
        btn_import.pack(side="left", padx=(0, 10))
        
        btn_manual = ctk.CTkButton(header_frame, text="➕ Add Lead Manually", command=self._on_manual_add_click, width=140)
        btn_manual.pack(side="left", padx=(0, 10))
        
        self.search_entry = ctk.CTkEntry(header_frame, placeholder_text="🔍 Search leads by name, phone, company...", width=280)
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self._on_search_keypress)
        
        # Filters dropdowns
        self.filter_status = ctk.CTkOptionMenu(
            header_frame, 
            values=["Status: All", "Status: Pending", "Status: Sent", "Status: Failed", "Status: Invalid"],
            command=self._on_filter_changed,
            width=130
        )
        self.filter_status.pack(side="left", padx=(0, 10))
        
        self.filter_company = ctk.CTkOptionMenu(
            header_frame,
            values=["Company: All"],
            command=self._on_filter_changed,
            width=150
        )
        self.filter_company.pack(side="left")
        
        # -------------------------------------------------------------
        # LEFT COLUMN - LEADS TREEVIEW TABLE
        # -------------------------------------------------------------
        left_pane = ctk.CTkFrame(frame)
        left_pane.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_pane.grid_rowconfigure(1, weight=1)
        left_pane.grid_columnconfigure(0, weight=1)
        
        # Table stats line
        table_top = ctk.CTkFrame(left_pane, fg_color="transparent", height=30)
        table_top.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.select_all_var = tk.BooleanVar(value=False)
        self.chk_select_all = ctk.CTkCheckBox(
            table_top, 
            text="Select All", 
            variable=self.select_all_var, 
            command=self._on_select_all_toggled,
            font=ctk.CTkFont(size=12)
        )
        self.chk_select_all.pack(side="left")
        
        self.lbl_selected_counter = ctk.CTkLabel(table_top, text="Selected: 0/0 leads", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_selected_counter.pack(side="right")
        
        # Treeview setup
        tree_frame = ctk.CTkFrame(left_pane, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        cols = ("select", "name", "phone", "company", "status", "date")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        
        # Set headers and widths
        headers = {
            "select": ("🔘", 35),
            "name": ("Lead Name", 140),
            "phone": ("Phone Number", 110),
            "company": ("Company", 110),
            "status": ("Status", 80),
            "date": ("Last Contact", 100)
        }
        
        for col_name, (heading, width) in headers.items():
            self.tree.heading(col_name, text=heading, anchor="center" if col_name == "select" else "w")
            self.tree.column(col_name, width=width, minwidth=width, stretch=True if col_name != "select" else False)
            
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Bind table click actions
        self.tree.bind("<ButtonRelease-1>", self._on_tree_row_clicked)
        self.tree.bind("<Double-1>", self._on_tree_row_double_clicked)
        
        # Table bottom: Action buttons
        table_bot = ctk.CTkFrame(left_pane, fg_color="transparent")
        table_bot.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        btn_export_sent = ctk.CTkButton(
            table_bot, 
            text="📤 Export Sent", 
            fg_color="transparent", 
            border_width=1, 
            text_color=("gray10", "gray90"),
            command=lambda: self._export_filtered_report("sent"),
            width=110
        )
        btn_export_sent.pack(side="left", padx=(0, 10))
        
        btn_export_failed = ctk.CTkButton(
            table_bot, 
            text="📤 Export Failed", 
            fg_color="transparent", 
            border_width=1, 
            text_color=("gray10", "gray90"),
            command=lambda: self._export_filtered_report("failed"),
            width=110
        )
        btn_export_failed.pack(side="left")

        # -------------------------------------------------------------
        # RIGHT COLUMN - COMPOSER, ATTACHMENTS & DISPATCH CONTROLS
        # -------------------------------------------------------------
        right_pane = ctk.CTkScrollableFrame(frame)
        right_pane.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        right_pane.grid_columnconfigure(0, weight=1)
        
        # Message Composer Section
        comp_title = ctk.CTkLabel(right_pane, text="1. Message Composer", font=ctk.CTkFont(size=14, weight="bold"))
        comp_title.grid(row=0, column=0, sticky="w", pady=5)
        
        # Template selector dropdown
        self.tpl_selector_var = tk.StringVar(value="Select Template")
        self.tpl_selector = ctk.CTkOptionMenu(
            right_pane,
            variable=self.tpl_selector_var,
            values=["Select Template"],
            command=self._on_template_selected
        )
        self.tpl_selector.grid(row=1, column=0, sticky="ew", pady=5)
        
        # Textarea
        self.txt_message = ctk.CTkTextbox(right_pane, height=180, font=("Courier New", 12))
        self.txt_message.grid(row=2, column=0, sticky="ew", pady=5)
        self.txt_message.bind("<KeyRelease>", self._on_message_txt_keypress)
        
        # Placeholders panel
        lbl_placeholders = ctk.CTkLabel(right_pane, text="Insert Placeholder:", font=ctk.CTkFont(size=11), text_color="gray50")
        lbl_placeholders.grid(row=3, column=0, sticky="w", pady=(2, 0))
        
        pl_frame = ctk.CTkFrame(right_pane, fg_color="transparent")
        pl_frame.grid(row=4, column=0, sticky="ew", pady=2)
        
        placeholders = [
            ("Name", "{{name}}"),
            ("Company", "{{company}}"),
            ("Phone", "{{phone}}"),
            ("Email", "{{email}}")
        ]
        for idx, (label, tag) in enumerate(placeholders):
            pl_btn = ctk.CTkButton(
                pl_frame,
                text=f"+ {label}",
                font=ctk.CTkFont(size=11),
                fg_color=("gray85", "gray25"),
                hover_color=("gray75", "gray35"),
                text_color=("gray10", "gray90"),
                width=65,
                height=24,
                command=lambda t=tag: self._insert_placeholder(t)
            )
            pl_btn.pack(side="left", padx=3)
            
        # Message Preview Panel
        preview_title = ctk.CTkLabel(right_pane, text="Message Preview", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray50")
        preview_title.grid(row=5, column=0, sticky="w", pady=(10, 2))
        
        self.txt_preview = ctk.CTkTextbox(right_pane, height=120, font=("Segoe UI", 11), fg_color=("gray95", "gray15"), text_color="gray50")
        self.txt_preview.grid(row=6, column=0, sticky="ew", pady=2)
        self.txt_preview.configure(state="disabled")

        # Attachment Panel
        attach_title = ctk.CTkLabel(right_pane, text="2. Attach Brochure / Catalog (Optional)", font=ctk.CTkFont(size=14, weight="bold"))
        attach_title.grid(row=7, column=0, sticky="w", pady=(15, 5))
        
        attach_frame = ctk.CTkFrame(right_pane)
        attach_frame.grid(row=8, column=0, sticky="ew", pady=2)
        attach_frame.grid_columnconfigure(0, weight=1)
        
        self.chk_attachment_var = tk.BooleanVar(value=False)
        self.chk_attachment = ctk.CTkCheckBox(
            attach_frame, 
            text="Enable Attachment", 
            variable=self.chk_attachment_var, 
            command=self._on_attachment_toggled
        )
        self.chk_attachment.grid(row=0, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        
        self.lbl_attachment_name = ctk.CTkLabel(
            attach_frame, 
            text="No file selected (PDF, PNG, JPG supported)", 
            font=ctk.CTkFont(size=11), 
            text_color="gray50",
            anchor="w"
        )
        self.lbl_attachment_name.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="ew")
        
        self.btn_browse_attach = ctk.CTkButton(
            attach_frame, 
            text="Browse File", 
            command=self._on_browse_attachment_click,
            width=90,
            state="disabled"
        )
        self.btn_browse_attach.grid(row=1, column=1, padx=10, pady=(0, 8), sticky="e")

        # Scheduling Panel
        sched_title = ctk.CTkLabel(right_pane, text="3. Schedule Campaign (Optional)", font=ctk.CTkFont(size=14, weight="bold"))
        sched_title.grid(row=9, column=0, sticky="w", pady=(15, 5))
        
        sched_frame = ctk.CTkFrame(right_pane)
        sched_frame.grid(row=10, column=0, sticky="ew", pady=2)
        sched_frame.grid_columnconfigure(0, weight=1)
        sched_frame.grid_columnconfigure(1, weight=1)
        
        self.chk_sched_var = tk.BooleanVar(value=False)
        self.chk_sched = ctk.CTkCheckBox(
            sched_frame, 
            text="Schedule Future Run", 
            variable=self.chk_sched_var, 
            command=self._on_sched_toggled
        )
        self.chk_sched.grid(row=0, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        
        self.lbl_sched_date = ctk.CTkLabel(sched_frame, text="Date (YYYY-MM-DD):", font=ctk.CTkFont(size=11), state="disabled")
        self.lbl_sched_date.grid(row=1, column=0, padx=10, pady=2, sticky="w")
        
        self.ent_sched_date = ctk.CTkEntry(sched_frame, placeholder_text="YYYY-MM-DD", state="disabled")
        self.ent_sched_date.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        self.lbl_sched_time = ctk.CTkLabel(sched_frame, text="Time (HH:MM:SS):", font=ctk.CTkFont(size=11), state="disabled")
        self.lbl_sched_time.grid(row=1, column=1, padx=10, pady=2, sticky="w")
        
        self.ent_sched_time = ctk.CTkEntry(sched_frame, placeholder_text="HH:MM:SS", state="disabled")
        self.ent_sched_time.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="ew")

        # Dispatch Queue Settings & Controls
        dispatch_title = ctk.CTkLabel(right_pane, text="4. Campaign Dispatch Controls", font=ctk.CTkFont(size=14, weight="bold"))
        dispatch_title.grid(row=11, column=0, sticky="w", pady=(15, 5))
        
        ctrl_frame = ctk.CTkFrame(right_pane)
        ctrl_frame.grid(row=12, column=0, sticky="ew", pady=2)
        ctrl_frame.grid_columnconfigure(0, weight=1)
        
        # Delay slider
        self.lbl_delay = ctk.CTkLabel(ctrl_frame, text="Delay: 5 seconds (interval between sends)", font=ctk.CTkFont(size=12))
        self.lbl_delay.grid(row=0, column=0, columnspan=3, padx=15, pady=(15, 5), sticky="w")
        
        self.slider_delay = ctk.CTkSlider(ctrl_frame, from_=3, to=15, number_of_steps=12, command=self._on_delay_slider_changed)
        self.slider_delay.grid(row=1, column=0, columnspan=3, padx=15, pady=(0, 15), sticky="ew")
        self.slider_delay.set(self.settings.sender_delay)
        self._on_delay_slider_changed(self.settings.sender_delay)
        
        # Action Buttons: Start, Pause, Stop
        actions_btn_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        actions_btn_frame.grid(row=2, column=0, columnspan=3, padx=15, pady=(0, 15), sticky="ew")
        actions_btn_frame.grid_columnconfigure(0, weight=1)
        actions_btn_frame.grid_columnconfigure(1, weight=1)
        actions_btn_frame.grid_columnconfigure(2, weight=1)
        
        self.btn_start = ctk.CTkButton(
            actions_btn_frame, 
            text="▶ Start Campaign", 
            fg_color="#10b981", 
            hover_color="#059669",
            command=self._on_start_campaign_click
        )
        self.btn_start.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.btn_pause = ctk.CTkButton(
            actions_btn_frame, 
            text="⏸ Pause", 
            fg_color="#eab308", 
            hover_color="#ca8a04",
            command=self._on_pause_campaign_click,
            state="disabled"
        )
        self.btn_pause.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.btn_stop = ctk.CTkButton(
            actions_btn_frame, 
            text="⏹ Stop", 
            fg_color="#ef4444", 
            hover_color="#dc2626",
            command=self._on_stop_campaign_click,
            state="disabled"
        )
        self.btn_stop.grid(row=0, column=2, padx=5, sticky="ew")
        
        # Progress and status widgets
        self.prog_bar = ctk.CTkProgressBar(ctrl_frame)
        self.prog_bar.grid(row=3, column=0, columnspan=3, padx=15, pady=(10, 5), sticky="ew")
        self.prog_bar.set(0)
        
        self.lbl_progress_status = ctk.CTkLabel(ctrl_frame, text="Ready. Choose leads and compose message.", font=ctk.CTkFont(size=11), text_color="gray50")
        self.lbl_progress_status.grid(row=4, column=0, columnspan=3, padx=15, pady=(0, 15), sticky="w")
        
        return frame

    def _create_templates_frame(self) -> ctk.CTkFrame:
        """Generates the Template Builder view (save, edit, delete message templates)."""
        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)  # Left list
        frame.grid_columnconfigure(1, weight=2)  # Right editor
        frame.grid_rowconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(frame, text="Message Templates", font=ctk.CTkFont(size=22, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
        
        # Left Panel - Templates List
        left_pane = ctk.CTkFrame(frame)
        left_pane.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_pane.grid_rowconfigure(1, weight=1)
        left_pane.grid_columnconfigure(0, weight=1)
        
        list_lbl = ctk.CTkLabel(left_pane, text="Saved Templates", font=ctk.CTkFont(size=14, weight="bold"))
        list_lbl.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.lst_templates = tk.Listbox(
            left_pane,
            font=("Segoe UI", 10),
            bg=self.settings.app_theme.lower() == "dark" and "#1e1e1e" or "#ffffff",
            fg=self.settings.app_theme.lower() == "dark" and "#ffffff" or "#000000",
            selectbackground="#1f6aa5",
            highlightthickness=0
        )
        self.lst_templates.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        self.lst_templates.bind("<<ListboxSelect>>", self._on_template_list_selected)
        
        btn_new_tpl = ctk.CTkButton(left_pane, text="➕ Create New Template", command=self._on_new_template_click)
        btn_new_tpl.grid(row=2, column=0, padx=15, pady=15, sticky="ew")

        # Right Panel - Template Editor
        right_pane = ctk.CTkFrame(frame)
        right_pane.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        right_pane.grid_rowconfigure(3, weight=1)
        right_pane.grid_columnconfigure(0, weight=1)
        
        editor_lbl = ctk.CTkLabel(right_pane, text="Template Editor", font=ctk.CTkFont(size=14, weight="bold"))
        editor_lbl.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="w")
        
        # Name input
        self.ent_tpl_name = ctk.CTkEntry(right_pane, placeholder_text="Template Name (e.g. Welcome Brochure)")
        self.ent_tpl_name.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        # Help label
        tpl_desc = ctk.CTkLabel(
            right_pane, 
            text="Body (Supported Placeholders: {{name}}, {{company}}, {{phone}}, {{email}})",
            font=ctk.CTkFont(size=11),
            text_color="gray50"
        )
        tpl_desc.grid(row=2, column=0, padx=20, pady=(5, 0), sticky="w")
        
        # Text Body
        self.txt_tpl_body = ctk.CTkTextbox(right_pane, font=("Courier New", 12))
        self.txt_tpl_body.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")
        
        # Placeholders insertion panel
        tpl_pl_frame = ctk.CTkFrame(right_pane, fg_color="transparent")
        tpl_pl_frame.grid(row=4, column=0, padx=20, pady=2, sticky="ew")
        
        placeholders = [
            ("Name", "{{name}}"),
            ("Company", "{{company}}"),
            ("Phone", "{{phone}}"),
            ("Email", "{{email}}")
        ]
        for idx, (label, tag) in enumerate(placeholders):
            pl_btn = ctk.CTkButton(
                tpl_pl_frame,
                text=f"+ {label}",
                font=ctk.CTkFont(size=11),
                fg_color=("gray85", "gray25"),
                hover_color=("gray75", "gray35"),
                text_color=("gray10", "gray90"),
                width=65,
                height=24,
                command=lambda t=tag: self._insert_template_placeholder(t)
            )
            pl_btn.pack(side="left", padx=3)
            
        # Action Buttons: Save & Delete
        tpl_actions = ctk.CTkFrame(right_pane, fg_color="transparent")
        tpl_actions.grid(row=5, column=0, padx=20, pady=15, sticky="ew")
        tpl_actions.grid_columnconfigure(0, weight=1)
        tpl_actions.grid_columnconfigure(1, weight=1)
        
        self.btn_save_tpl = ctk.CTkButton(
            tpl_actions,
            text="💾 Save Template",
            fg_color="#10b981",
            hover_color="#059669",
            command=self._on_save_template_click
        )
        self.btn_save_tpl.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.btn_delete_tpl = ctk.CTkButton(
            tpl_actions,
            text="🗑️ Delete Template",
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._on_delete_template_click
        )
        self.btn_delete_tpl.grid(row=0, column=1, padx=5, sticky="ew")
        
        return frame

    def _create_logs_frame(self) -> ctk.CTkFrame:
        """Generates the System Logs view."""
        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(frame, text="Activity Logs", font=ctk.CTkFont(size=22, weight="bold"))
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Logs Container
        logs_inner = ctk.CTkFrame(frame)
        logs_inner.grid(row=1, column=0, sticky="nsew")
        logs_inner.grid_columnconfigure(0, weight=1)
        logs_inner.grid_rowconfigure(1, weight=1)
        
        # Toolbar
        toolbar = ctk.CTkFrame(logs_inner, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        btn_clear = ctk.CTkButton(toolbar, text="🗑️ Clear Screen", command=self._on_clear_logs_click, width=120)
        btn_clear.pack(side="left", padx=(0, 10))
        
        btn_export = ctk.CTkButton(toolbar, text="💾 Export Logs to Excel", command=self._on_export_logs_click, width=160)
        btn_export.pack(side="left")
        
        # Textbox logs console
        self.txt_logs = ctk.CTkTextbox(logs_inner, font=("Courier New", 10), fg_color=("gray95", "gray15"))
        self.txt_logs.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.txt_logs.configure(state="disabled")
        
        return frame

    def _create_settings_frame(self) -> ctk.CTkFrame:
        """Generates the Settings configuration view."""
        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(frame, text="Configuration Settings", font=ctk.CTkFont(size=22, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
        
        # Left Panel - API Connection Card
        api_card = ctk.CTkFrame(frame)
        api_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=5)
        api_card.grid_columnconfigure(0, weight=1)
        
        api_title = ctk.CTkLabel(api_card, text="WhatsApp Cloud API", font=ctk.CTkFont(size=15, weight="bold"))
        api_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")
        
        # Access Token
        lbl_token = ctk.CTkLabel(api_card, text="Access Token (Bearer token):", font=ctk.CTkFont(size=12))
        lbl_token.grid(row=1, column=0, padx=20, pady=2, sticky="w")
        
        self.ent_token = ctk.CTkEntry(api_card, show="*")
        self.ent_token.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.ent_token.insert(0, self.settings.access_token)
        
        # Toggle Token Visibility
        self.show_token_var = tk.BooleanVar(value=False)
        self.chk_show_token = ctk.CTkCheckBox(
            api_card, 
            text="Show Token", 
            variable=self.show_token_var, 
            command=self._on_show_token_toggled,
            font=ctk.CTkFont(size=11)
        )
        self.chk_show_token.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")
        
        # Phone ID
        lbl_phone_id = ctk.CTkLabel(api_card, text="Phone Number ID:", font=ctk.CTkFont(size=12))
        lbl_phone_id.grid(row=4, column=0, padx=20, pady=2, sticky="w")
        
        self.ent_phone_id = ctk.CTkEntry(api_card)
        self.ent_phone_id.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.ent_phone_id.insert(0, self.settings.phone_number_id)
        
        # API Version
        lbl_version = ctk.CTkLabel(api_card, text="API Version:", font=ctk.CTkFont(size=12))
        lbl_version.grid(row=6, column=0, padx=20, pady=2, sticky="w")
        
        self.ent_version = ctk.CTkEntry(api_card)
        self.ent_version.grid(row=7, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.ent_version.insert(0, self.settings.api_version)
        
        # Test Credentials Connection Button
        self.btn_test_conn = ctk.CTkButton(
            api_card,
            text="⚡ Test API Connection",
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._on_test_connection_click
        )
        self.btn_test_conn.grid(row=8, column=0, padx=20, pady=(5, 20), sticky="ew")

        # Right Panel - Preferences Card
        pref_card = ctk.CTkFrame(frame)
        pref_card.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=5)
        pref_card.grid_columnconfigure(0, weight=1)
        
        pref_title = ctk.CTkLabel(pref_card, text="System Preferences", font=ctk.CTkFont(size=15, weight="bold"))
        pref_title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")
        
        # Sound notification toggle
        self.chk_sound_var = tk.BooleanVar(value=self.settings.play_sound)
        self.chk_sound = ctk.CTkCheckBox(
            pref_card,
            text="Play notification sound on completion",
            variable=self.chk_sound_var
        )
        self.chk_sound.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        
        # Retry limit
        lbl_retry = ctk.CTkLabel(pref_card, text="Failed message retry attempts (0-3):", font=ctk.CTkFont(size=12))
        lbl_retry.grid(row=2, column=0, padx=20, pady=2, sticky="w")
        
        self.opt_retry = ctk.CTkOptionMenu(pref_card, values=["0", "1", "2", "3"])
        self.opt_retry.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.opt_retry.set(str(self.settings.retry_limit))
        
        # Company Logo setup (customization support)
        lbl_logo = ctk.CTkLabel(pref_card, text="Upload Company Logo (renders in Sidebar):", font=ctk.CTkFont(size=12))
        lbl_logo.grid(row=4, column=0, padx=20, pady=2, sticky="w")
        
        logo_sub_frame = ctk.CTkFrame(pref_card, fg_color="transparent")
        logo_sub_frame.grid(row=5, column=0, padx=20, pady=(0, 15), sticky="ew")
        logo_sub_frame.grid_columnconfigure(0, weight=1)
        
        self.lbl_logo_path = ctk.CTkLabel(logo_sub_frame, text="Default assets logo active", font=ctk.CTkFont(size=11), text_color="gray50", anchor="w")
        self.lbl_logo_path.grid(row=0, column=0, sticky="ew")
        
        btn_logo = ctk.CTkButton(logo_sub_frame, text="Upload", width=70, command=self._on_logo_upload_click)
        btn_logo.grid(row=0, column=1, sticky="e", padx=(5, 0))

        # Bottom Bar: General Save Settings Button
        save_frame = ctk.CTkFrame(frame, fg_color="transparent")
        save_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=20)
        
        self.btn_save_settings = ctk.CTkButton(
            save_frame,
            text="💾 Save Configurations",
            fg_color="#10b981",
            hover_color="#059669",
            command=self._on_save_settings_click,
            height=40
        )
        self.btn_save_settings.pack(fill="x")
        
        return frame

    # =========================================================================
    # EVENT HANDLERS & CALLBACK TRIGGER GLUES
    # =========================================================================

    def _on_show_token_toggled(self) -> None:
        """Toggles password masking on the API Access Token input field."""
        if self.show_token_var.get():
            self.ent_token.configure(show="")
        else:
            self.ent_token.configure(show="*")

    def _on_import_leads_click(self) -> None:
        """Triggers system filepicker to select lead sheet, passes selection to callbacks."""
        file_path = filedialog.askopenfilename(
            title="Import Excel or CSV Leads File",
            filetypes=[("Excel / CSV files", "*.xlsx *.xls *.csv"), ("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv")]
        )
        if file_path:
            self.selected_file_path = file_path
            if "import_leads" in self.callbacks:
                self.callbacks["import_leads"](file_path)

    def _on_search_keypress(self, event) -> None:
        """Fires live filtering on text input change."""
        self._filter_and_refresh_leads()

    def _on_filter_changed(self, choice: str) -> None:
        """Refreshes visible records in Treeview when a filter value is modified."""
        self._filter_and_refresh_leads()

    def _on_select_all_toggled(self) -> None:
        """Selects or deselects all currently visible leads in the table list."""
        select_state = self.select_all_var.get()
        # Toggle checkbox column character in Treeview for all shown elements
        for item in self.tree.get_children():
            # Get underlying lead item using tags
            self.tree.set(item, column="select", value="☑" if select_state else "☐")
            lead_idx = int(item)
            if 0 <= lead_idx < len(self.leads_data):
                self.leads_data[lead_idx]["selected"] = select_state
                
        self._update_selected_count()

    def toggle_lead_selection(self, item_id: str) -> None:
        """Toggles the checkmark on an individual lead row."""
        current_val = self.tree.set(item_id, column="select")
        new_val = "☑" if current_val == "☐" else "☐"
        self.tree.set(item_id, column="select", value=new_val)
        
        lead_idx = int(item_id)
        if 0 <= lead_idx < len(self.leads_data):
            self.leads_data[lead_idx]["selected"] = (new_val == "☑")
            
        self._update_selected_count()
        self._update_message_preview(lead_idx)

    def _on_tree_row_clicked(self, event) -> None:
        """Detects clicks in the grid view. Toggles check if selection column is hit, else updates preview."""
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if not item_id:
            return
            
        if column == "#1":  # 'select' checkbox column
            self.toggle_lead_selection(item_id)
        else:
            # Highlight index for previewing
            lead_idx = int(item_id)
            self._update_message_preview(lead_idx)

    def _on_tree_row_double_clicked(self, event) -> None:
        """Double clicking a row toggles its checkmark selection."""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.toggle_lead_selection(item_id)

    def _insert_placeholder(self, tag: str) -> None:
        """Inserts a template placeholder tag at the cursor position in the message composer textbox."""
        try:
            self.txt_message.insert("insert", tag)
            self._update_message_preview(self.current_preview_index)
        except Exception:
            pass

    def _insert_template_placeholder(self, tag: str) -> None:
        """Inserts a template placeholder tag at the cursor position in the template builder textbox."""
        try:
            self.txt_tpl_body.insert("insert", tag)
        except Exception:
            pass

    def _on_message_txt_keypress(self, event) -> None:
        """Dynamically updates the live preview panel content as the user types message templates."""
        self._update_message_preview(self.current_preview_index)

    def _on_attachment_toggled(self) -> None:
        """Enables/disables the file attachment browse button."""
        state = "normal" if self.chk_attachment_var.get() else "disabled"
        self.btn_browse_attach.configure(state=state)

    def _on_browse_attachment_click(self) -> None:
        """Opens file selection dialog for media files (PDF, image, etc.)."""
        file_path = filedialog.askopenfilename(
            title="Select Attachment (Brochure / Image)",
            filetypes=[
                ("All Supported Files", "*.pdf *.png *.jpg *.jpeg"),
                ("PDF Documents", "*.pdf"),
                ("Images", "*.png *.jpg *.jpeg")
            ]
        )
        if file_path:
            self.attachment_file_path = file_path
            path_obj = Path(file_path)
            size_mb = path_obj.stat().st_size / (1024 * 1024)
            self.lbl_attachment_name.configure(
                text=f"{path_obj.name} ({size_mb:.2f} MB)",
                text_color=("gray10", "gray90")
            )
            if size_mb > 5 and path_obj.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                messagebox.showwarning(
                    "Large Media Warning",
                    "Images larger than 5MB may fail WhatsApp sending guidelines. "
                    "Consider compressing or using PDFs."
                )

    def _on_sched_toggled(self) -> None:
        """Enables/disables scheduling fields."""
        status = "normal" if self.chk_sched_var.get() else "disabled"
        self.lbl_sched_date.configure(state=status)
        self.ent_sched_date.configure(state=status)
        self.lbl_sched_time.configure(state=status)
        self.ent_sched_time.configure(state=status)
        
        # Populate defaults
        if self.chk_sched_var.get():
            now = datetime.now()
            # Default YYYY-MM-DD
            self.ent_sched_date.delete(0, "end")
            self.ent_sched_date.insert(0, now.strftime("%Y-%m-%d"))
            
            # Default time +1 hour
            future_time = now + timedelta(hours=1)
            self.ent_sched_time.delete(0, "end")
            self.ent_sched_time.insert(0, future_time.strftime("%H:%M:%S"))

    def _on_delay_slider_changed(self, value: float) -> None:
        """Updates label when delay configuration slider is moved."""
        self.lbl_delay.configure(text=f"Delay: {int(value)} seconds (interval between sends)")

    def _on_start_campaign_click(self) -> None:
        """Validates configuration and triggers controller to launch dispatch thread."""
        if "start_campaign" in self.callbacks:
            self.callbacks["start_campaign"]()

    def _on_pause_campaign_click(self) -> None:
        """Toggles thread pausing state."""
        if "pause_campaign" in self.callbacks:
            self.callbacks["pause_campaign"]()

    def _on_stop_campaign_click(self) -> None:
        """Signals background dispatch thread to abort completely."""
        if "stop_campaign" in self.callbacks:
            self.callbacks["stop_campaign"]()

    def _on_new_template_click(self) -> None:
        """Clears the template editor fields for drafting a new template."""
        self.ent_tpl_name.delete(0, "end")
        self.txt_tpl_body.delete("1.0", "end")
        self.lst_templates.selection_clear(0, "end")

    def _on_template_list_selected(self, event) -> None:
        """Loads template information from list selection into the editor panel."""
        selection = self.lst_templates.curselection()
        if not selection:
            return
            
        index = selection[0]
        tpl_name = self.lst_templates.get(index)
        
        if "load_template_to_editor" in self.callbacks:
            self.callbacks["load_template_to_editor"](tpl_name)

    def _on_save_template_click(self) -> None:
        """Saves current template text input to local storage."""
        name = self.ent_tpl_name.get().strip()
        body = self.txt_tpl_body.get("1.0", "end").strip()
        
        if "save_template" in self.callbacks:
            self.callbacks["save_template"](name, body)

    def _on_delete_template_click(self) -> None:
        """Deletes selected template."""
        name = self.ent_tpl_name.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Select a template to delete.")
            return
            
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete template '{name}'?"):
            if "delete_template" in self.callbacks:
                self.callbacks["delete_template"](name)

    def _on_clear_logs_click(self) -> None:
        """Clears console screen logs."""
        self.txt_logs.configure(state="normal")
        self.txt_logs.delete("1.0", "end")
        self.txt_logs.configure(state="disabled")

    def _on_export_logs_click(self) -> None:
        """Prompts target location to save sending history logs as Excel file."""
        export_path = filedialog.asksaveasfilename(
            title="Export Activity Logs",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if export_path and "export_logs" in self.callbacks:
            self.callbacks["export_logs"](export_path)

    def _on_test_connection_click(self) -> None:
        """Performs lightweight WhatsApp connection testing using temporary parameters."""
        token = self.ent_token.get().strip()
        phone_id = self.ent_phone_id.get().strip()
        version = self.ent_version.get().strip()
        
        if not token or not phone_id:
            messagebox.showwarning("Incomplete Settings", "Access Token and Phone Number ID are required to run tests.")
            return
            
        self.btn_test_conn.configure(state="disabled", text="Testing...")
        if "test_api_connection" in self.callbacks:
            self.callbacks["test_api_connection"](token, phone_id, version)

    def _on_save_settings_click(self) -> None:
        """Saves values from configuration panels to settings files."""
        token = self.ent_token.get().strip()
        phone_id = self.ent_phone_id.get().strip()
        version = self.ent_version.get().strip()
        sound = self.chk_sound_var.get()
        retry = int(self.opt_retry.get())
        
        if "save_settings" in self.callbacks:
            self.callbacks["save_settings"](token, phone_id, version, sound, retry)

    def _on_logo_upload_click(self) -> None:
        """Handles selecting customized brand logos."""
        file_path = filedialog.askopenfilename(
            title="Select Company Logo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif")]
        )
        if file_path:
            if "save_logo" in self.callbacks:
                self.callbacks["save_logo"](file_path)

    def _on_template_selected(self, choice: str) -> None:
        """Triggered when template option is changed in Campaign Manager."""
        if choice == "Select Template":
            return
            
        if "load_template_to_composer" in self.callbacks:
            self.callbacks["load_template_to_composer"](choice)

    def _export_filtered_report(self, status: str) -> None:
        """Export leads matching particular status (sent/failed)."""
        export_path = filedialog.asksaveasfilename(
            title=f"Export {status.capitalize()} Leads Report",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if export_path and "export_filtered_leads" in self.callbacks:
            self.callbacks["export_filtered_leads"](status, export_path)

    # =========================================================================
    # PUBLIC VIEW INTERACTION INTERFACES
    # =========================================================================

    def display_leads_table(self, leads: List[Dict[str, Any]]) -> None:
        """Loads lead list into local memory state, configures filters, and renders rows."""
        self.leads_data = leads
        
        # Prepopulate selection flags if not set
        for lead in self.leads_data:
            if "selected" not in lead:
                lead["selected"] = lead.get("is_valid", False)  # Auto select valid leads by default
                
        # Fetch unique company list for filter dropdown
        companies = sorted(list(set(str(l.get("company", "")).strip() for l in leads if str(l.get("company", "")).strip())))
        company_filter_values = ["Company: All"] + [f"Company: {c}" for c in companies]
        self.filter_company.configure(values=company_filter_values)
        self.filter_company.set("Company: All")
        
        self._filter_and_refresh_leads()

    def _filter_and_refresh_leads(self) -> None:
        """Filters leads list based on search, status, and company selections, then populates Treeview."""
        search_query = self.search_entry.get().strip().lower()
        status_filter = self.filter_status.get()
        company_filter = self.filter_company.get()
        
        # Clear current rows
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.filtered_leads = []
        
        for idx, lead in enumerate(self.leads_data):
            # 1. Search Query filter
            if search_query:
                match_search = (
                    search_query in lead["name"].lower() or
                    search_query in lead["phone"].lower() or
                    search_query in lead["company"].lower() or
                    search_query in lead["email"].lower()
                )
                if not match_search:
                    continue
                    
            # 2. Status dropdown filter
            if status_filter != "Status: All":
                target_status = status_filter.replace("Status: ", "").lower()
                # Handle mapping validation status
                lead_status = lead["status"].lower()
                if target_status == "invalid" and not lead["is_valid"]:
                    pass  # Show it
                elif lead_status != target_status:
                    continue
                    
            # 3. Company dropdown filter
            if company_filter != "Company: All":
                target_company = company_filter.replace("Company: ", "").strip()
                if lead["company"].strip() != target_company:
                    continue
                    
            # Render Row
            check_char = "☑" if lead.get("selected", False) else "☐"
            
            # Choose color tag based on lead status
            tag = "valid"
            if not lead["is_valid"]:
                tag = "invalid"
                if lead.get("is_duplicate", False):
                    tag = "duplicate"
            elif lead["status"].lower() == "sent":
                tag = "sent"
            elif lead["status"].lower() == "failed":
                tag = "failed"
                
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    check_char,
                    lead["name"],
                    lead["phone"],
                    lead["company"],
                    lead["status"],
                    lead["last_contact_date"]
                ),
                tags=(tag,)
            )
            self.filtered_leads.append(lead)

        # Style configurations for tags
        self.tree.tag_configure("valid", foreground=("#1f6aa5", "#60a5fa"))
        self.tree.tag_configure("invalid", background=("#fca5a5", "#7f1d1d"), foreground=("#000000", "#ffffff"))
        self.tree.tag_configure("duplicate", background=("#fef08a", "#78350f"), foreground=("#000000", "#ffffff"))
        self.tree.tag_configure("sent", foreground=("#10b981", "#34d399"))
        self.tree.tag_configure("failed", foreground=("#ef4444", "#f87171"))
        
        self._update_selected_count()
        
        # Reset preview index
        if self.filtered_leads:
            self._update_message_preview(0)
        else:
            self._update_message_preview(-1)

    def _update_selected_count(self) -> None:
        """Recalculates select count statistics and updates campaign labels."""
        total_shown = len(self.tree.get_children())
        selected_count = sum(1 for lead in self.leads_data if lead.get("selected", False))
        total_leads = len(self.leads_data)
        
        self.lbl_selected_counter.configure(text=f"Selected: {selected_count} / {total_leads} leads")
        
        # Determine select all state
        visible_indices = [int(item) for item in self.tree.get_children()]
        if not visible_indices:
            self.select_all_var.set(False)
        else:
            all_visible_selected = all(self.leads_data[idx].get("selected", False) for idx in visible_indices)
            self.select_all_var.set(all_visible_selected)

    def _update_message_preview(self, lead_idx: int) -> None:
        """Parses active message template for selected lead and populates message preview pane."""
        self.current_preview_index = lead_idx
        
        self.txt_preview.configure(state="normal")
        self.txt_preview.delete("1.0", "end")
        
        if lead_idx < 0 or lead_idx >= len(self.leads_data):
            self.txt_preview.insert("1.0", "No lead selected or imported.")
            self.txt_preview.configure(state="disabled")
            return
            
        lead = self.leads_data[lead_idx]
        template = self.txt_message.get("1.0", "end").strip()
        
        if not template:
            self.txt_preview.insert("1.0", "Draft template message above to see preview.")
            self.txt_preview.configure(state="disabled")
            return
            
        # Call placeholder replacement
        if "replace_placeholders" in self.callbacks:
            preview_text = self.callbacks["replace_placeholders"](template, lead)
            self.txt_preview.insert("1.0", preview_text)
            
        self.txt_preview.configure(state="disabled")

    def update_dashboard_metrics(self, stats: Dict[str, Any]) -> None:
        """Loads current metrics variables into Dashboard value widgets."""
        for key, val_widget in self.dash_cards.items():
            if key in stats:
                val_widget.configure(text=str(stats[key]))
                
        # Construct summary label
        summary_text = (
            f"• File Imported: {self.selected_file_path and Path(self.selected_file_path).name or 'None'}\n"
            f"• Queue Status: {stats.get('pending', 0)} Messages Pending\n"
            f"• Successes Rate: {stats.get('success_rate', '0%')}\n"
            f"• Average Interval Delay: {self.settings.sender_delay}s\n"
            f"• Retry Max Limit: {self.settings.retry_limit} times"
        )
        self.lbl_summary_desc.configure(text=summary_text)

    def update_connection_status_lbl(self, status_text: str, success: bool = True) -> None:
        """Changes style and message text of connection indicator on Dashboard/Settings."""
        color = "#10b981" if success else "#ef4444"
        self.lbl_conn_status.configure(text=status_text, text_color=color)

    def populate_templates_dropdown(self, template_names: List[str]) -> None:
        """Configures templates selector dropdown in Campaign Manager."""
        list_vals = ["Select Template"] + template_names
        self.tpl_selector.configure(values=list_vals)
        if template_names:
            self.tpl_selector.set("Select Template")

    def update_templates_listbox(self, template_names: List[str]) -> None:
        """Configures template entries list under template manager screen."""
        self.lst_templates.delete(0, "end")
        for name in template_names:
            self.lst_templates.insert("end", name)

    def fill_template_editor(self, name: str, body: str) -> None:
        """Loads configuration fields on template form."""
        self.ent_tpl_name.delete(0, "end")
        self.ent_tpl_name.insert(0, name)
        
        self.txt_tpl_body.delete("1.0", "end")
        self.txt_tpl_body.insert("1.0", body)

    def append_log(self, text: str) -> None:
        """Appends formatted terminal log lines onto system logs dashboard."""
        self.txt_logs.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.insert("end", f"[{timestamp}] {text}\n")
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def set_sending_controls_state(self, status: str) -> None:
        """
        Adjusts button statuses during campaign sending execution.
        States: 'idle', 'sending', 'paused'
        """
        if status == "sending":
            self.btn_start.configure(state="disabled", text="⚡ Dispatching...")
            self.btn_pause.configure(state="normal", text="⏸ Pause")
            self.btn_stop.configure(state="normal")
            
            # Disable configuration fields
            self.txt_message.configure(state="disabled")
            self.chk_attachment.configure(state="disabled")
            self.btn_browse_attach.configure(state="disabled")
            self.chk_sched.configure(state="disabled")
            self.ent_sched_date.configure(state="disabled")
            self.ent_sched_time.configure(state="disabled")
            self.slider_delay.configure(state="disabled")
            
        elif status == "paused":
            self.btn_start.configure(state="disabled")
            self.btn_pause.configure(state="normal", text="▶ Resume")
            self.btn_stop.configure(state="normal")
            
        else: # idle / ready
            self.btn_start.configure(state="normal", text="▶ Start Campaign")
            self.btn_pause.configure(state="disabled", text="⏸ Pause")
            self.btn_stop.configure(state="disabled")
            
            # Enable configurations
            self.txt_message.configure(state="normal")
            self.chk_attachment.configure(state="normal")
            if self.chk_attachment_var.get():
                self.btn_browse_attach.configure(state="normal")
            self.chk_sched.configure(state="normal")
            if self.chk_sched_var.get():
                self.ent_sched_date.configure(state="normal")
                self.ent_sched_time.configure(state="normal")
            self.slider_delay.configure(state="normal")

    def update_progress(self, sent: int, total: int, status_msg: str = "") -> None:
        """Sets metrics on dispatch controls progressbar."""
        if total > 0:
            fraction = sent / total
            self.prog_bar.set(fraction)
            if not status_msg:
                status_msg = f"Sending {sent} of {total} messages ({int(fraction*100)}%)"
        else:
            self.prog_bar.set(0)
            status_msg = "No queue elements."
            
        self.lbl_progress_status.configure(text=status_msg)

    def load_company_logo(self, image_path: str) -> None:
        """Loads and draws logo file inside the sidebar section."""
        try:
            if not os.path.exists(image_path):
                return
                
            path = Path(image_path)
            # Re-draw the top widget with Pillow
            img = Image.open(path)
            img = img.resize((60, 60), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Create a label with image if we decide to draw, or put inside sidebar
            # For simplicity, render label with logo image
            # Create/Update logo widgets in sidebar
            if hasattr(self, "sidebar_logo_img"):
                self.sidebar_logo_img.configure(image=photo)
                self.sidebar_logo_img.image = photo  # keep reference
            else:
                self.sidebar_logo_img = ctk.CTkLabel(self.sidebar_frame, image=photo, text="")
                # Insert logo widget at row 0 column 0, pushes rest down
                self.sidebar_logo_img.image = photo
                
                # Relayout top titles
                self.logo_label.grid_forget()
                self.subtitle_label.grid_forget()
                
                self.sidebar_logo_img.grid(row=0, column=0, padx=20, pady=(15, 5))
                self.logo_label.grid(row=1, column=0, padx=20, pady=(0, 2))
                self.subtitle_label.grid(row=2, column=0, padx=20, pady=(0, 15))
                self.separator.grid(row=3, column=0, padx=20, pady=(0, 20))
                
                # Shift Nav rows down
                for tid, btn in self.nav_btns.items():
                    info = btn.grid_info()
                    btn.grid(row=int(info["row"]) + 1, column=0)
                    
            self.lbl_logo_path.configure(text=f"Custom logo: {path.name}", text_color="#10b981")
            
        except Exception as e:
            self.append_log(f"Error loading company logo: {e}")

    def _on_manual_add_click(self) -> None:
        """Opens popup dialog to manually create a lead."""
        ManualLeadDialog(self, self.callbacks.get("add_manual_lead"))


class ManualLeadDialog(ctk.CTkToplevel):
    """Popup dialog for manually entering lead information."""
    
    def __init__(self, parent: Any, callback: Callable):
        super().__init__(parent)
        self.callback = callback
        
        self.title("Add Lead Manually")
        self.geometry("420x520")
        self.resizable(False, False)
        
        # Make the dialog modal and grab focus
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        
        # Grid config
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Container frame
        main_frame = ctk.CTkFrame(self, corner_radius=0)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Header Label
        lbl_title = ctk.CTkLabel(main_frame, text="Create Lead Entry", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_title.grid(row=0, column=0, columnspan=2, pady=(15, 20))
        
        # 1. Phone number (Mandatory)
        lbl_phone = ctk.CTkLabel(main_frame, text="Phone Number (Required)*:", anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_phone.grid(row=1, column=0, columnspan=2, padx=20, pady=(5, 2), sticky="w")
        self.ent_phone = ctk.CTkEntry(main_frame, placeholder_text="e.g. 9876543210 or +919999988888")
        self.ent_phone.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        
        # 2. Name (Optional)
        lbl_name = ctk.CTkLabel(main_frame, text="Lead Name (Optional):", anchor="w")
        lbl_name.grid(row=3, column=0, columnspan=2, padx=20, pady=(5, 2), sticky="w")
        self.ent_name = ctk.CTkEntry(main_frame, placeholder_text="e.g. John Doe")
        self.ent_name.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        
        # 3. Email (Optional)
        lbl_email = ctk.CTkLabel(main_frame, text="Email Address (Optional):", anchor="w")
        lbl_email.grid(row=5, column=0, columnspan=2, padx=20, pady=(5, 2), sticky="w")
        self.ent_email = ctk.CTkEntry(main_frame, placeholder_text="e.g. john@example.com")
        self.ent_email.grid(row=6, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        
        # 4. Company (Optional)
        lbl_company = ctk.CTkLabel(main_frame, text="Company (Optional):", anchor="w")
        lbl_company.grid(row=7, column=0, columnspan=2, padx=20, pady=(5, 2), sticky="w")
        self.ent_company = ctk.CTkEntry(main_frame, placeholder_text="e.g. Sooftcode")
        self.ent_company.grid(row=8, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        
        # 5. Last Contact Date (Optional)
        lbl_date = ctk.CTkLabel(main_frame, text="Last Contact Date (Optional):", anchor="w")
        lbl_date.grid(row=9, column=0, columnspan=2, padx=20, pady=(5, 2), sticky="w")
        self.ent_date = ctk.CTkEntry(main_frame, placeholder_text="YYYY-MM-DD")
        self.ent_date.grid(row=10, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        # Prepopulate with today's date
        self.ent_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # Buttons: Save & Cancel
        btn_cancel = ctk.CTkButton(main_frame, text="Cancel", fg_color=("gray75", "gray30"), hover_color=("gray65", "gray40"), text_color=("gray10", "gray90"), command=self.destroy)
        btn_cancel.grid(row=11, column=0, padx=(20, 10), pady=10, sticky="ew")
        
        btn_save = ctk.CTkButton(main_frame, text="Save Lead", fg_color="#10b981", hover_color="#059669", command=self._on_save)
        btn_save.grid(row=11, column=1, padx=(10, 20), pady=10, sticky="ew")
        
    def _on_save(self) -> None:
        phone = self.ent_phone.get().strip()
        name = self.ent_name.get().strip()
        email = self.ent_email.get().strip()
        company = self.ent_company.get().strip()
        date = self.ent_date.get().strip()
        
        if not phone:
            messagebox.showwarning("Incomplete Form", "Phone number is compulsory.")
            return
            
        if self.callback:
            success, err_msg = self.callback(phone, name, email, company, date)
            if success:
                self.destroy()
            else:
                messagebox.showerror("Error", err_msg)
        else:
            self.destroy()
