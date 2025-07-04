"""Main GUI Logic and application entry point"""

# Standard Library Imports
import sys
import os
import logging
import time
import datetime
import shutil
import json


# PyQt6 GUI Imports 
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
QApplication, QMainWindow, QPushButton, QLabel, QFileDialog,
QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QCheckBox, QSpinBox,
QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
QFrame, QGraphicsOpacityEffect, QDialog, QInputDialog,
QScrollArea, QProgressBar, QSizePolicy, QHeaderView, QStackedLayout
)

from PyQt6.QtGui import QPixmap, QIcon, QFont, QMovie
from PyQt6.QtCore import Qt, QTimer, QSize

# Matplotlib Backend for PyQt6
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("Qt5Agg")  # Ensure Matplotlib uses PyQt6 instead of TkAgg
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# ConoBot Imports
from middleware.cfgutils import ConfigManager
from frontend.setup_manager import SetupManager

# Configure Logging to Include Line Numbers
LOG_FILE = "ui_rendering.log"
logging.basicConfig (
filename=LOG_FILE,
level=logging.ERROR,
format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)

class AssetManager:
	"""
	Manages assets like images and icons.
	"""
	@staticmethod
	def get_asset_path(filename, fallback="default_image.png"):
		# ✅ Define Assets Directory
		ASSETS_DIR = "/usr/share/conobot/assets/"
		"""Returns the full path of an asset, using a fallback if the file is missing."""
		path = os.path.join(ASSETS_DIR, filename)
		if not os.path.exists(path):
			logging.warning(f"⚠ Asset not found: {path}. Using fallback: {fallback}")
			path = os.path.join(ASSETS_DIR, fallback)
			if not os.path.exists(path):
				logging.critical(f"❌ Fallback asset also missing: {path}. UI may break!")
			return path
		return path

	def setupConnections(self):
		"""Connects UI buttons to their respective functions."""
		if hasattr(self, 'next_button'):
			self.next_button.clicked.connect(self.handle_next_step)

		if hasattr(self, 'exit_assay_button'):
			self.exit_button.clicked.connect(self.exit_assay)

		if hasattr(self, 'finish_button'):
			self.finish_button.clicked.connect(self.finish_assay)  # ⏩ Calls `finish_assay()`

		logging.info("✅ UI connections successfully set up.")

	def resizeEvent(self, event):
		"""Handle window resize events to properly scale the background."""
		super().resizeEvent(event)
		
		# Update background size
		self.background_label.setGeometry(0, 0, self.width(), self.height())
		
		# Scale background content based on step
		if self.current_step in [2, 4]:
			# Loading screen (static PNG)
			if hasattr(self.background_label, 'pixmap') and not self.background_label.pixmap().isNull():
				pixmap = QPixmap(self.get_asset_path("cone_snail_loading.png"))
				self.background_label.setPixmap(pixmap.scaled(
					self.width(), 
					self.height(),
					Qt.AspectRatioMode.KeepAspectRatioByExpanding
				))
		else:
			# Default animated background (GIF)
			if hasattr(self, 'background_movie') and self.background_movie:
				self.background_movie.setScaledSize(self.size())

class UIStyle:
	"""Applies a universal stylesheet to ensure all UI elements have rounded corners and cohesive styling."""
	def apply_global_stylesheet(self):
		"""Applies a universal stylesheet to ensure all UI elements have rounded corners and cohesive styling."""
		qss_path = "/usr/share/conobot/assets/styles.qss"
		if os.path.exists(qss_path):
			try:
				with open(qss_path, "r") as file:
					global_stylesheet = file.read()
					self.setStyleSheet(global_stylesheet)
					logging.info(f"✅ Stylesheet applied successfully from {qss_path}.")
			except Exception as e:
				logging.error(f"❌ Failed to apply stylesheet: {str(e)}")
		else:
			logging.error(f"❌ Stylesheet file not found at {qss_path}.")
    
class ConoBotMainUI(QMainWindow):
	"""
	Main UI class for ConoBot.
	"""
	def __init__(self):

		# Create central widget and main layout
		self.central_widget = QWidget()
		self.setCentralWidget(self.central_widget)
		self.main_layout = QVBoxLayout(self.central_widget)
		self.main_layout.setContentsMargins(0, 0, 0, 0)
		self.main_layout.setSpacing(0)

		# Create background container that will hold either static or animated background
		self.background_container = QWidget()
		self.background_container.setObjectName("background")
		self.background_container.setStyleSheet("#background { background-color: #001a33; }")
		
		# Create background label that will display the image/animation
		self.background_label = QLabel(self.background_container) 
		background_layout = QVBoxLayout(self.background_container)
		background_layout.setContentsMargins(0, 0, 0, 0)
		background_layout.addWidget(self.background_label)
		
		# Add background container as first widget in main layout
		self.main_layout.addWidget(self.background_container)

		# Set appropriate background based on step
		if self.current_step in [2, 4]:
			# Static loading screen background
			background_path = self.get_asset_path("cone_snail_loading.png")
			if os.path.exists(background_path):
				pixmap = QPixmap(background_path)
				self.background_label.setPixmap(pixmap)
				self.background_label.setScaledContents(True)
		else:
			# Animated background
			background_path = self.get_asset_path("oceanic_background.gif") 
			if os.path.exists(background_path):
				self.background_movie = QMovie(background_path)
				self.background_label.setMovie(self.background_movie)
				self.background_movie.start()
			else:
				logging.warning(f"⚠ Background image missing: {background_path}")

		# Create container for navigation buttons (next and finish)
		self.progression_button_container = QWidget()
		self.progression_button_layout = QHBoxLayout(self.progression_button_container)
		self.progression_button_layout.setContentsMargins(10, 5, 10, 10)  # Add some padding
		self.progression_button_layout.addStretch()  # Push buttons to the right
	
		# Initialize next_button
		self.next_button = QPushButton("Next ➡")
		self.next_button.setStyleSheet(
			"background-color: #28A745; color: white; padding: 4px 10px; border-radius: 8px; font-size: 12px;"
		)
		self.next_button.setFixedSize(80, 30)  # ✅ Small, compact button
		
		# Initialize finish_button
		self.finish_button = QPushButton("Finish Assay!")
		self.finish_button.setStyleSheet(
			"background-color: #007AFF; color: white; padding: 5px; border-radius: 10px;"
			"font-weight: bold; font-family: Open Sans; font-size: 15px;"
		)
		
		# Add buttons to the container (they will occupy the same space)
		self.progression_button_layout.addWidget(self.next_button)
		self.progression_button_layout.addWidget(self.finish_button)
		
		# Manage button sizes
		self.next_button.setFixedSize(80, 30)  # ✅ Small, compact button
		self.finish_button.setFixedSize(80, 30)  # ✅ Small, compact button

		# Add Progression Button Container to Main Layout
		self.main_layout.addWidget(self.progression_button_container)
		
		# ✅ Exit Button Setup - Always at top left
		self.exit_button = QPushButton()
		icon_path = self.get_asset_path("exit_icon.png")
		if os.path.exists(icon_path):
			icon_pixmap = QPixmap(icon_path)
			icon = QIcon(icon_pixmap)
			self.exit_button.setIcon(icon)
			self.exit_button.setIconSize(icon_pixmap.size())
		else:
			logging.warning(f"⚠ Exit icon missing: {icon_path}")
			self.exit_button.setText("×")  # Fallback to text 'x'

		self.exit_button.setFixedSize(30, 30)  # ✅ Compact button size
		self.exit_button.setStyleSheet("background: transparent; border: none;")

		# Add Exit Button to Main Layout
		self.main_layout.addWidget(self.exit_button)

		# Position exit button at top-left corner
		self.exit_button.setParent(self)
		self.exit_button.move(10, 10)  # Fixed position at top-left with 10px margin
		self.exit_button.raise_()  # Ensure button stays on top of other widgets

		# ✅ Progress Bar Setup
		self.progress_bar_container = QWidget()
		self.progress_bar_layout = QHBoxLayout()
		self.progress_bar_container.setLayout(self.progress_bar_layout)

		# Create progress bar before adding it to layout
		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setValue(0)
		self.progress_bar.setContentsMargins(10, 10, 10, 10)
		self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.progress_bar.setFixedWidth(300)  # Set fixed width to prevent stretching across screen

		# Add widgets to layout with proper centering
		self.progress_bar_layout.addStretch(1)  # Add stretch before widgets to center them
		self.progress_bar_layout.addWidget(QLabel("Progress:"))
		self.progress_bar_layout.addWidget(self.progress_bar)
		self.progress_bar_layout.addStretch(1)  # Add stretch after widgets to center them

		# Center the entire layout
		self.progress_bar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

		# ✅ Ensure these dictionaries are properly initialized
		self.deconvolution_results = {}
		self.amide_mapping_results = {}
		self.manual_inputs = {}

		# ✅ Ensure essential attributes exist **before any function calls**
		self.assay_name = None  # 🔥 Fix for `save_autosave()` error
		self.required_fields = {}  # 🔥 Fix for missing `required_fields`
		self.current_step = 0  # 🔥 Ensures `current_step` is initialized early

		# ✅ Load Configuration Using ConfigManager
		self.config = ConfigManager.load_config() or {}

		# ✅ First-time Setup Check
		setup_needed = not self.config.get("setup_complete", False)

		if setup_needed:
			logging.warning("⚠ First-time setup required, launching setup UI...")
			SetupManager.run_initial_setup(self)
			self.config = ConfigManager.load_config()  # Reload config after setup

		# ✅ Assign Key Config Variables
		self.api_key = self.config.get("full_api_key", "")
		self.organization_id = self.config.get("full_organization_id", None)
		self.auto_save_enabled = self.config.get("auto_save", True)
		self.ui_scaling = self.config.get("ui_scaling", 1.0)
		
		# ✅ Ensure Required Directories Exist
		os.makedirs("ConoBot Utilities", exist_ok=True)
		self.data_directory = self.config.get("storage_path", os.path.expanduser("ConoBot Utilities/data"))
		os.makedirs(self.data_directory, exist_ok=True)
		os.makedirs("ConoBot Utilities/logs", exist_ok=True)
		os.makedirs("ConoBot Utilities/storage", exist_ok=True)

		# ✅ UI Configuration
		self.setStyleSheet(f"font-size: {max(10, int(12 * self.ui_scaling))}px;")

		# ✅ Initialize Matplotlib Graph (Before UI Setup)
		self.figure, self.ax = plt.subplots()
		self.canvas = FigureCanvas(self.figure)

		# ✅ Initialize UI Safely
		QApplication.processEvents()  # ✅ Prevents Freezing
		try:
			self.initUI()
		except Exception as e:
			logging.error(f"❌ UI Initialization Failed: {str(e)}")
			QMessageBox.critical(self, "Error", "UI initialization failed. Check logs.")
			return  # ✅ Prevents execution if UI fails

		# ✅ UI Enhancements
		self.apply_global_stylesheet()
		self.fade_in_ui()

		# ✅ Load Autosave (Only if Available)
		try:
			self.load_autosave()
			self.update_ui_on_step_change()
		except Exception as e:
			logging.warning(f"⚠ Failed to load autosave: {str(e)}")

		# ✅ Setup UI Button Connections
		self.setupConnections()

		# ✅ Ensure navigation buttons exist
		for btn_name in ["next_button", "finish_button", "exit_assay_button"]:
			if not hasattr(self, btn_name):
				setattr(self, btn_name, None)
		
		# ✅ Ensure Main UI Loads Only If Setup is Complete
		if setup_needed:
			logging.info("🚀 First-time setup detected. Launching setup UI...")
			SetupManager.run_initial_setup(self)
		else:
			logging.info("✅ Setup complete. Initializing main UI...")
			self.initialize_main_ui()
	
	def initUI(self):
		"""Initializes ConoBot's GUI, setting up the home screen layout with navigation and assay selection panels."""
		
		try:
			# ✅ Ensure QApplication exists
			if QApplication.instance() is None:
				logging.critical("❌ QApplication instance missing!")
				QMessageBox.critical(None, "Error", "QApplication must be initialized first.")
				return
			
			logging.info("🔹 Initializing ConoBot UI...")

			# ✅ Set Main Window Properties
			self.setWindowTitle("ConoBot - Spectral Analysis")
			self.setGeometry(100, 100, 1200, 800)

			# ✅ Apply Global Stylesheet
			self.apply_global_stylesheet()

			# ✅ Create Home Screen Layout
			self.home_layout = QHBoxLayout()
			self.home_screen = QWidget()
			self.home_screen.setLayout(self.home_layout)

			# ✅ Sidebar for Navigation Buttons (Invisible, just a container)
			self.sidebar_layout = QVBoxLayout()
			self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
			self.add_navigation_buttons()  # Add buttons to the sidebar layout
			self.home_screen.setLayout(self.sidebar_layout)

			# ✅ Title Panel
			self.setup_title_and_citation()

			self.setup_assay_grid()  # Setup assay grid within this layout

			# ✅ Ensure UI Prevents Freezing
			QApplication.processEvents()
			logging.info("✅ ConoBot UI initialization complete.")

			# ✅ Fade-in Effect for Enhanced UX
			self.fade_in_ui()

		except Exception as e:
			logging.error(f"❌ Error during UI initialization: {str(e)}", exc_info=True)
			QMessageBox.critical(None, "UI Initialization Error", f"Failed to initialize UI: {str(e)}", exc_info=True)
	
	def setup_app_icon(self):
		"""Sets up the application icon and background image with fallbacks if missing."""

		logging.info("🔹 Setting up app icon...")

		# ✅ Set Application Icon (Check existence first)
		icon_path = self.get_asset_path("conobot_icon.png")
		self.setWindowIcon(QIcon(icon_path))

		logging.info("✅ App icon set successfully.")

	def setup_title_and_citation(self):
		"""Creates and sets up the title panel and ConoServer citation section."""

		logging.info("🔹 Setting up title and citation panels...")

		# 🔹 Title Panel
		self.title_panel = QLabel("ConoBot - Select an Assay or Create a New One")
		self.title_panel.setFont(QFont("Arial", 18, QFont.Weight.Bold))
		self.title_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.title_panel.setStyleSheet("border-radius: 15px; background: rgba(0, 0, 50, 0.8); color: white; padding: 10px;")
		self.main_layout.addWidget(self.title_panel)

		# 🔹 ConoServer Citation Panel
		self.citation_panel = QLabel(
			"<h3 style='color:white; text-align:center;'>🔬 Powered by ConoServer (& GPT-4o) and Created by Luke Levensaler</h3>"
			"<p style='color:white; font-size:12px; text-align:center; max-width: 800px; margin: 0 auto;'>"
			"Kaas, Q., Yu, R., Jin, A. H., Dutertre, S., & Craik, D. J. (2012). "
			"ConoServer: Updated content, knowledge, and discovery tools in the conopeptide database. "
			"<i>Nucleic Acids Research, 40</i>(D1), D325-D330. "
			"<a href='https://doi.org/10.1093/nar/gkr886' style='color:cyan;'>https://doi.org/10.1093/nar/gkr886</a></p>"
		)
		self.citation_panel.setStyleSheet(
			"background: rgba(0, 0, 50, 0.8);"
			"border-radius: 10px;"
			"padding: 10px;"
			"margin-top: 20px;"
		)

		self.citation_panel.setOpenExternalLinks(True)
		self.citation_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.citation_panel.setStyleSheet("border-radius: 10px; background: navy; color: white; padding: 8px;")
		self.main_layout.addWidget(self.citation_panel)

		logging.info("✅ Title and citation panels set successfully.")
		
	def open_assay(self, assay_name):
		"""Opens the selected assay, ensuring correct step transition and UI state."""
		logging.info(f"📂 Opening Assay: {assay_name}")
		self.assay_name = assay_name

		# ✅ Ensure UI elements exist before modifying them
		if hasattr(self, "title_panel"):
			self.title_panel.setText(f"Current Assay: {assay_name}")

		# ✅ Hide Main Screen Elements & Clear Overlap
		self.home_screen.setVisible(False)
		self.hide_all_ui_elements()

		# ✅ Start at Step 1 (Smoothing)
		self.current_step = 1
		self.update_ui_on_step_change()

		# ✅ Ensure UI updates smoothly
		if hasattr(self, "assay_screen"):
			self.assay_screen.setVisible(True)
		else:
			logging.error("❌ 'assay_screen' is missing. Assay UI may not load correctly.")

		# ✅ Apply fade-in effect
		self.fade_in_ui()  # 🔥 Ensures findings appear smoothly
	
	def prompt_assay_name(self):
		"""Prompt user for an assay name and allow them to select a thumbnail image."""

		# ✅ Ask for Assay Name
		text, ok = QInputDialog.getText(self, "New Assay", "Enter assay name:")

		if not ok or not text.strip():
			logging.warning("❌ Assay creation canceled.")
			return

		assays = self.get_saved_assays()
		assay_name = text.strip()

		if assay_name in assays:
			QMessageBox.warning(self, "Error", "Assay name already exists. Choose a different name.")
			return  # ✅ Re-prompt if duplicate name is entered

		# ✅ Open File Dialog for Image Selection
		image_path, _ = QFileDialog.getOpenFileName(
			self, "Choose a Cool Picture of Your Snail!", "", "Images (*.png *.jpg *.jpeg)"
		)

		if not image_path:
			logging.warning("⚠ No image selected. Using default thumbnail.")
			image_path = self.get_asset_path("default_thumbnail.png")

		# ✅ Ensure valid paths before proceeding
		if not os.path.exists(image_path):
			logging.error(f"❌ Selected image does not exist: {image_path}. Using fallback.")
			image_path = self.get_asset_path("default_thumbnail.png")

		# ✅ Create the Assay and Store the Thumbnail
		self.create_assay(assay_name, image_path)

	def setup_assay_grid(self):
		"""Sets up the scrollable assay grid layout."""

		logging.info("🔹 Setting up assay grid...")

		# ✅ Scrollable Assay Area
		self.scroll_area = QScrollArea()
		self.scroll_area.setWidgetResizable(True)

		# ✅ Assay Grid (Ensures proper spacing & infinite scrolling)
		self.assay_grid = QGridLayout()
		self.assay_grid.setSpacing(15)

		# ✅ Assay Panels (Google Docs-like)
		self.assay_container = QWidget()
		self.assay_container.setLayout(self.assay_grid)
		self.scroll_area.setWidget(self.assay_container)

		# Ensure home_screen has a layout
		if not self.home_screen.layout():
			self.home_screen.setLayout(QVBoxLayout())

		# Add scroll_area to the layout of home_screen
		self.home_screen.layout().addWidget(self.scroll_area)

		# ✅ Load Assays into the Grid
		self.load_assays()

		logging.info("✅ Assay grid setup complete.")
	
	def load_assays(self):
		"""
		Load saved assays into a scrollable, infinitely scrolling grid layout, ensuring 3 assays per row.
		No default assays—home screen starts empty until a new assay is created.
		"""

		# ✅ Ensure we're in Step 0 before loading assays
		if not hasattr(self, "current_step") or self.current_step != 0:
			logging.warning("⚠ Assay loading attempted outside Step 0. Ignoring.")
			return

		if not hasattr(self, 'assay_grid'):
			self.assay_grid = QGridLayout()
			self.assay_grid.setSpacing(15)  # ✅ Maintain consistent spacing

		# ✅ Load assay metadata (thumbnails)
		metadata_file = os.path.join(self.data_directory, "assays_metadata.json")
		metadata = {}

		if os.path.exists(metadata_file):
			try:
				with open(metadata_file, "r") as file:
					metadata = json.load(file)
					if not isinstance(metadata, dict):
						raise ValueError("Invalid metadata format")
			except (json.JSONDecodeError, ValueError) as e:
				logging.error(f"❌ Failed to load metadata: {e}")
				metadata = {}

		# ✅ Clear existing widgets before reloading (prevents UI duplication)
		if hasattr(self, "assay_grid") and isinstance(self.assay_grid, QGridLayout):
			while self.assay_grid.count():
				item = self.assay_grid.takeAt(0)
				if item.widget() and isinstance(item.widget(), QWidget):
					item.widget().setParent(None)  # Instead of deleteLater() to avoid Qt errors

		# ✅ Load saved assays (Remove defaults)
		saved_assays = self.get_saved_assays()

		if not saved_assays:
			logging.info("🔹 No assays found. Home screen remains empty until a new assay is created.")
			return  # ✅ Prevents any default panels from showing up

		# ✅ Configure Scrollable Container
		self.scroll_widget = QWidget()
		self.scroll_layout = QVBoxLayout()
		self.scroll_widget.setLayout(self.scroll_layout)
		self.scroll_layout.setSpacing(10)
		self.scroll_area.setWidgetResizable(True)
		self.scroll_area.setWidget(self.scroll_widget)

		# ✅ Invisible Grid Layout with Infinite Vertical Scroll
		grid_widget = QWidget()
		grid_layout = QGridLayout()
		grid_layout.setSpacing(15)  # Ensure correct spacing
		grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # ✅ Prevents horizontal stretching

		for index, assay in enumerate(saved_assays):
			# ✅ Retrieve thumbnail path (use default if missing)
			image_path = metadata.get(assay, {}).get("thumbnail", "default_thumbnail.png")
			image_path = self.get_asset_path(image_path)

			# ✅ Assay Container (Holds Button & Label)
			self.assay_container = QWidget()
			self.assay_layout = QVBoxLayout()
			self.assay_container.setLayout(self.assay_layout)
			self.assay_layout.setContentsMargins(5, 5, 5, 5)

			# ✅ Assay Button (Stored as an instance variable to prevent garbage collection)
			if not hasattr(self, f"assay_button_{assay}"):
				self.__dict__[f"assay_button_{assay}"] = QPushButton("", self)
			assay_button = self.__dict__[f"assay_button_{assay}"]
			assay_button.setFixedSize(200, 150)
			assay_button.setStyleSheet(
				"QPushButton {"
				"    border-radius: 15px;"
				"    background-image: url('" + image_path.replace("'", "\\'") + "');"
				"    background-position: center;"
				"    background-repeat: no-repeat;"
				"}"
				"QPushButton:hover {"
				"    opacity: 0.8;"
				"}"
			)

			assay_button.clicked.connect(lambda _, name=assay: self.open_assay(name))

			# ✅ Assay Name Label (Overlay)
			assay_label = QLabel(assay, assay_button)
			assay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			assay_label.setStyleSheet(
				"background: rgba(0, 0, 0, 0.5);"
				"color: white;"
				"font-weight: bold;"
				"font-size: 14px;"
				"padding: 5px;"
				"border-radius: 8px;"
			)


			# ✅ Delete Button (Stored as an instance variable to prevent garbage collection)
			if not hasattr(self, f"delete_button_{assay}"):
				self.__dict__[f"delete_button_{assay}"] = QPushButton("", self)
			delete_button = self.__dict__[f"delete_button_{assay}"]
			trash_icon_path = os.path.join(os.path.dirname(__file__), "assets/trash_icon.png")
			if os.path.exists(trash_icon_path):
				delete_button.setIcon(QIcon(trash_icon_path))
			else:
				logging.warning(f"⚠ Trash icon missing: {trash_icon_path}")

			delete_button.setFixedSize(32, 32)
			delete_button.setStyleSheet(
				"QPushButton {"
				"    border: none;"
				"    background: transparent;"
				"}"
				"QPushButton:hover {"
				"    background-color: rgba(255, 0, 0, 0.5);"
				"}"
			)

			delete_button.clicked.connect(lambda _, name=assay: self.delete_assay(name))

			# ✅ Layout for Delete Button (Bottom Right)
			delete_layout = QHBoxLayout()
			delete_layout.addStretch()
			delete_layout.addWidget(delete_button)

			# ✅ Add Elements to Assay Layout
			self.assay_layout.addWidget(assay_button)
			self.assay_layout.addWidget(assay_label)  # ✅ Ensures label overlays thumbnail
			# ✅ Add Delete Button Layout to Assay Container
			self.assay_layout.addLayout(delete_layout)

			# ✅ Add Assay Container to Grid (3 per row)
			grid_layout.addWidget(self.assay_container, index // 3, index % 3)
			
			# ✅ Add to Main Scrollable Layout
			self.scroll_layout.addWidget(self.scroll_area)
			self.scroll_widget.setLayout(self.scroll_layout)

			# ✅ Replace the Home Screen Assay Grid
			if hasattr(self, "scroll_area"):
				self.scroll_area.setWidget(self.scroll_widget)
			else:
				logging.error("❌ 'scroll_area' not found. Assay list may not display correctly.")

			logging.info("✅ Assays loaded successfully into grid with infinite scrolling.")

	def add_navigation_buttons(self):
		"""Creates and adds sidebar navigation buttons with icons, ensuring they only appear on the main screen (Step 0)."""

		# ✅ Ensure navigation buttons only appear in Step 0 (Main Screen)
		if self.current_step != 0:
			logging.warning("⚠ Navigation buttons can only be added in Step 0 (Main Screen). Skipping...")
			return

		# ✅ Clear existing buttons if re-running this function (prevents duplicates)
		while self.sidebar_layout.count():
			item = self.sidebar_layout.takeAt(0)
			widget = item.widget()
			if widget:
				widget.deleteLater()

		# ✅ Store buttons for toggling active state
		self.nav_buttons = {}

		buttons = [
			("New Assay", "plus_icon.png", self.prompt_assay_name, "📂 Create a new assay"),
			("My Findings", "archive_icon.png", self.show_findings, "📑 View saved assay results"),
			("References", "book_icon.png", self.show_references, "📖 View scientific references"),
		]

		for tooltip, icon_name, action, description in buttons:
			button = QPushButton("", self)
			button.setCheckable(True)  # ✅ Enables toggle behavior (active/inactive)
			icon_path = os.path.join(os.path.dirname(__file__), f"assets/{icon_name}")

			if os.path.exists(icon_path):
				button.setIcon(QIcon(icon_path))
			else:
				logging.warning(f"⚠ {tooltip} icon missing: {icon_path}")

			button.setToolTip(f"{description}")
			button.setFixedSize(50, 50)
			button.setStyleSheet(
				"QPushButton {"
				"    border-radius: 15px;"
				"    background-color: rgba(255, 255, 255, 0.2);"
				"    padding: 5px;"
				"}"
				"QPushButton:hover {"
				"    background-color: rgba(255, 255, 255, 0.3);"
				"}"
				"QPushButton:checked {"
				"    background-color: rgba(0, 122, 255, 0.8);"
				"    color: white;"
				"}"  # ✅ MacOS-style blue highlight
			)

			button.clicked.connect(lambda _, b=button: self.set_active_nav_button(b, action))

			# ✅ Ensure button has no parent before adding to layout
			if button.parent() is not None:
				button.setParent(None)

			self.sidebar_layout.addWidget(button)
			self.nav_buttons[button] = action  # ✅ Store button-action mapping

		# ✅ Ensure sidebar_widget is properly set up and has no parent before adding
		if not hasattr(self, 'sidebar_widget'):
			self.sidebar_widget = QWidget()
			self.sidebar_widget.setLayout(self.sidebar_layout)

		if self.sidebar_widget.parent() is not None:
			self.sidebar_widget.setParent(None)

		# ✅ Ensure sidebar_widget is added exactly once
		if hasattr(self, 'home_screen') and isinstance(self.home_screen.layout(), QVBoxLayout):
			if self.sidebar_widget not in [self.home_screen.layout().itemAt(i).widget() for i in range(self.home_screen.layout().count())]:
				self.home_screen.layout().addWidget(self.sidebar_widget)

		logging.info("✅ Navigation buttons successfully added to the main screen.")
    
	def initialize_main_ui(self):
		"""Ensures ConoBot starts on the main home screen (Step 0) after the API key is set, avoiding layout duplication and crashes."""

		logging.info("🔹 Initializing Main UI...")

		# ✅ Now safely assign `main_layout` if it's not already set
		self.central_widget.setLayout(self.main_layout)
		logging.info("✅ Assigned `main_layout` to `central_widget` successfully.")

		# ✅ Force the user back to setup UI if setup is incomplete
		if not self.config.get("setup_complete", False):
			logging.warning("⚠ Setup incomplete. Redirecting user to initial setup.")
			SetupManager.run_initial_setup(self)
			return

		# ✅ Start UI at Step 0 (Home Screen)
		self.current_step = 0

		# ✅ Ensure UI transition follows workflow step change
		if hasattr(self, "update_ui_on_step_change") and callable(self.update_ui_on_step_change):
			self.update_ui_on_step_change()
		else:
			logging.error("❌ self.update_ui_on_step_change() is missing! Skipping UI update.")

		logging.info("✅ ConoBot successfully initialized to Step 0.")

		# ✅ Apply fade-in effect
		self.fade_in_ui()  # 🔥 Ensures smooth UI transitions

		# ✅ Ensure UI elements are refreshed safely
		QApplication.processEvents()

		logging.info("🔹 ConoBot is now ready for use!")

	def set_active_nav_button(self, clicked_button, action):
		"""
		Ensures only the clicked navigation button is highlighted (blue) and executes its action 
		while preventing navigation if required fields are missing.
		"""

		# ✅ Prevent navigation if required fields are not filled
		if not self.require_mandatory_input():
			logging.warning("⚠ Navigation blocked due to incomplete fields.")
			clicked_button.setChecked(False)  # ❌ Do not allow button to stay active
			QMessageBox.warning(self, "Incomplete Fields", "Please fill all required fields before proceeding.")
			return  # ⛔ Stop function execution

		# ✅ Deselect all other buttons
		for button in self.nav_buttons.keys():
			button.setChecked(False)

		# ✅ Highlight the clicked button
		clicked_button.setChecked(True)

		# ✅ Log successful navigation
		logging.info(f"✅ Navigation button activated.")

		# ✅ Execute the associated function
		try:
			action()
		except Exception as e:
			logging.error(f"❌ Error executing action: {str(e)}")
			QMessageBox.critical(self, "Navigation Error", f"An error occurred: {str(e)}")

	def setup_step_1_ui(self):
		"""Combines graph display, data upload/download, and smoothing controls for Step 2."""

		# Create a main layout for Step 2
		step_2_layout = QVBoxLayout()

		# --- Graph UI (Top Half) ---
		graph_container = QWidget()  # Container for graph and buttons
		graph_layout = QVBoxLayout(graph_container)  # Layout for the container

		# ✅ Ensure Figure and Axes exist
		if not hasattr(self, "figure") or not isinstance(self.figure, plt.Figure):
			self.figure = plt.figure(facecolor="white")

		if not hasattr(self, "ax") or not isinstance(self.ax, plt.Axes):
			self.ax = self.figure.add_subplot(111)

		# ✅ Style Matplotlib Graph
		self.ax.set_facecolor("white")
		self.ax.spines['top'].set_visible(False)
		self.ax.spines['right'].set_visible(False)
		self.ax.spines['left'].set_visible(False)
		self.ax.spines['bottom'].set_visible(False)
		self.ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.7)
		self.ax.plot(color="red", linewidth=2)  # Initial empty plot

		# ✅ Ensure `canvas` exists
		if not hasattr(self, "canvas") or not isinstance(self.canvas, FigureCanvas):
			self.canvas = FigureCanvas(self.figure)
			self.canvas.setStyleSheet("border-radius: 10px; background-color: white; padding: 5px;")

		graph_layout.addWidget(self.canvas)  # Add canvas to graph layout

		# --- Upload/Download Buttons (Top Right) ---
		csv_button_layout = QHBoxLayout()  # Layout for buttons

		# Upload Button with GIF icon
		self.upload_button = QPushButton()
		self.upload_button.setFixedSize(30, 30)
		self.upload_button.setStyleSheet("background-color: #007AFF; border-radius: 15px;")
		
		# Get upload icon path and create movie
		upload_icon_path = self.get_asset_path("upload_icon.gif")
		self.upload_movie = QMovie(upload_icon_path)
		self.upload_movie.jumpToFrame(0)  # Start at first frame but don't play
		self.upload_movie.setScaledSize(QSize(26, 26))  # Slightly smaller than button to respect borders
		
		# Create label to hold the movie inside the button
		self.upload_icon_label = QLabel()
		self.upload_icon_label.setMovie(self.upload_movie)
		self.upload_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		
		# Add label to button layout
		upload_layout = QHBoxLayout(self.upload_button)
		upload_layout.setContentsMargins(2, 2, 2, 2)  # Small margins to respect borders
		upload_layout.addWidget(self.upload_icon_label)
		
		# Connect button click to play animation and load CSV
		self.upload_button.clicked.connect(lambda: self.upload_movie.start())
		self.upload_button.clicked.connect(self.load_csv)
		csv_button_layout.addWidget(self.upload_button)

		# Download Button with GIF icon
		self.download_button = QPushButton()
		self.download_button.setFixedSize(30, 30)
		self.download_button.setStyleSheet("background-color: #007AFF; border-radius: 15px;")
		self.download_button.setEnabled(False)  # Initially disabled
		
		# Get download icon path and create movie
		download_icon_path = self.get_asset_path("download_button.gif")
		self.download_movie = QMovie(download_icon_path)
		self.download_movie.jumpToFrame(0)  # Start at first frame but don't play
		self.download_movie.setScaledSize(QSize(26, 26))  # Slightly smaller than button to respect borders
		
		# Create label to hold the movie inside the button
		self.download_icon_label = QLabel()
		self.download_icon_label.setMovie(self.download_movie)
		self.download_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		
		# Add label to button layout
		download_layout = QHBoxLayout(self.download_button)
		download_layout.setContentsMargins(2, 2, 2, 2)  # Small margins to respect borders
		download_layout.addWidget(self.download_icon_label)
		
		# Connect button click to play animation and download data
		self.download_button.clicked.connect(lambda: self.download_movie.start())
		self.download_button.clicked.connect(self.download_smoothed_data)
		csv_button_layout.addWidget(self.download_button)

		graph_layout.addLayout(csv_button_layout)  # Add button layout to graph layout

		step_2_layout.addWidget(graph_container)  # Add graph container to main layout

		# --- Smoothing Controls (Bottom Half) ---
		smoothing_container = QWidget()  # Container for smoothing controls
		smoothing_layout = QVBoxLayout(smoothing_container)  # Layout for the container

		# Label for Smoothing Section
		smoothing_label = QLabel("Apply Data Smoothing:")
		smoothing_label.setFont(QFont("Arial", 12))
		smoothing_layout.addWidget(smoothing_label)

		# Cubic Spline Checkbox
		if not hasattr(self, "cubic_spline_checkbox"):
			self.cubic_spline_checkbox = QCheckBox("Cubic Spline")
			# Add your cubic spline connection here
		smoothing_layout.addWidget(self.cubic_spline_checkbox)

		# FT Low-Pass Checkbox
		if not hasattr(self, "ft_lowpass_checkbox"):
			self.ft_lowpass_checkbox = QCheckBox("FT Low-Pass")
			# Add your FT low-pass connection here
		smoothing_layout.addWidget(self.ft_lowpass_checkbox)

		# Savitzky-Golay Checkbox
		if not hasattr(self, "savgol_checkbox"):
			self.savgol_checkbox = QCheckBox("Savitzky-Golay")
			self.savgol_checkbox.stateChanged.connect(self.toggle_savgol_controls)

		if self.savgol_checkbox.parent():
			self.savgol_checkbox.setParent(None)
		smoothing_layout.addWidget(self.savgol_checkbox)

		# Savitzky-Golay Parameter Fields
		if not hasattr(self, "savgol_params_widget"):
			self.savgol_params_widget = QWidget()
			self.savgol_params_layout = QVBoxLayout(self.savgol_params_widget)

			# Window Size SpinBox
			self.savgol_window_size = QSpinBox()
			self.savgol_window_size.setRange(3, 99)
			self.savgol_window_size.setSingleStep(2)  # Ensures only odd values
			self.savgol_window_size.valueChanged.connect(lambda: self.update_graph_view(self.data))

			# Polynomial Order SpinBox
			self.savgol_polyorder = QSpinBox()
			self.savgol_polyorder.setRange(1, 5)
			self.savgol_polyorder.valueChanged.connect(lambda: self.update_graph_view(self.data))

			# Add Parameter Inputs to Layout
			window_label = QLabel("Window Size:")
			poly_label = QLabel("Polynomial Order:")

			for widget in [window_label, self.savgol_window_size, poly_label, self.savgol_polyorder]:
				if widget.parent() is not None:
					widget.setParent(None)

			self.savgol_params_layout.addWidget(window_label)
			self.savgol_params_layout.addWidget(self.savgol_window_size)
			self.savgol_params_layout.addWidget(poly_label)
			self.savgol_params_layout.addWidget(self.savgol_polyorder)

		if self.savgol_params_widget.parent() is not None:
			self.savgol_params_widget.setParent(None)
		smoothing_layout.addWidget(self.savgol_params_widget)

		# AI Optimization Button
		if not hasattr(self, "ai_savgol_recommend_button"):
			self.ai_savgol_recommend_button = QPushButton("🤖 AI Recommend Smoothing")
			self.ai_savgol_recommend_button.setStyleSheet(
				"background-color: #4B0082; color: white; padding: 5px; border-radius: 10px;")
		if self.ai_savgol_recommend_button.parent() is not None:
			self.ai_savgol_recommend_button.setParent(None)
		smoothing_layout.addWidget(self.ai_savgol_recommend_button, alignment=Qt.AlignmentFlag.AlignCenter)

		# Bayesian Optimization Button
		if not hasattr(self, "bayesian_optimize_button"):
			self.bayesian_optimize_button = QPushButton("📊 Bayesian Optimization")
			self.bayesian_optimize_button.setCheckable(True)
		if self.bayesian_optimize_button.parent() is not None:
			self.bayesian_optimize_button.setParent(None)
		smoothing_layout.addWidget(self.bayesian_optimize_button, alignment=Qt.AlignmentFlag.AlignCenter)

		step_2_layout.addWidget(smoothing_container)  # Add smoothing container to main layout

		return step_2_layout
	
	def hide_all_ui_elements(self):
		"""Hides all UI elements to prevent overlap when switching assays."""

		# ✅ Ensure UI elements exist before attempting to hide them
		ui_elements = [
			"home_screen", "assay_screen", "graph_container", "progress_bar",
			"loading_screen", "results_ui", "findings_screen", "quantification_screen"
		]

		for element in ui_elements:
			widget = getattr(self, element, None)
			if widget and isinstance(widget, QWidget):
				widget.setVisible(False)

		# ✅ Ensure manual input fields are hidden safely
		if hasattr(self, 'manual_inputs') and isinstance(self.manual_inputs, dict):
			for key, widget in self.manual_inputs.items():
				if widget and isinstance(widget, QWidget):
					widget.setVisible(False)
				else:
					logging.warning(f"⚠ Attempted to hide non-existent manual input field: {key}")

	def show_references(self):

		"""Displays a window with scientific references in a scrollable layout."""
		
		if self.current_step != 0:  # ✅ References should only be accessed from the main screen
			logging.warning("⚠ References screen attempted outside Step 0. Ignoring.")
			return

		reference_window = QDialog(self)
		self.reference_layout = QVBoxLayout(reference_window)
		reference_window.resize(800, 600)
		
		self.scroll_area.setWidgetResizable(True)
		self.scroll_area.setWidget(self.scroll_widget)

		references = [
			("Gao et al. (2017)", "Cone Snails: A Big Store of Conotoxins for Novel Drug Discovery.",
				"https://doi.org/10.3390/toxins9120397"),

			("Imanishi et al. (2012)", "Zn(II) Binding and DNA Binding Properties of Ligand-Substituted CXHH-Type Zinc Finger Proteins.",
				"https://doi.org/10.1021/bi300236m"),

			("Krizek et al. (1993)", "Ligand variation and metal ion binding specificity in zinc finger peptides.",
				"https://doi.org/10.1021/ic00058a030"),

			("Lukács et al. (2021)", "Metal Binding Ability of Small Peptides Containing Cysteine Residues.",
				"https://doi.org/10.1002/open.202000304"),

			("Gencic et al. (2001)", "Zinc−Thiolate Intermediate in Catalysis of Methyl Group Transfer in Methanosarcina barkeri.",
				"https://doi.org/10.1021/bi0112917"),

			("Weyer & Lo (2006)", "Spectra-Structure Correlations in the Near-infrared.",
				"https://doi.org/10.1002/9780470027325.s4102"),
		]

		# ✅ Populate References Panel safely
		for ref in references:
			ref_panel = QLabel(f"<b>{ref[0]}</b><br>{ref[1]}<br><a href='{ref[2]}'>{ref[2]}</a>")
			ref_panel.setOpenExternalLinks(True)
			ref_panel.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
			ref_panel.setAlignment(Qt.AlignmentFlag.AlignLeft)
			ref_panel.setStyleSheet("border-radius: 10px; background: rgba(240, 240, 240, 0.9); padding: 10px; margin: 5px;")

			# ✅ Ensure no existing parent
			if ref_panel.parent() is not None:
				ref_panel.setParent(None)

			self.scroll_layout.addWidget(ref_panel) 

		reference_window.exec()