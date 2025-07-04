import os
import json
import logging
import shutil
import datetime
import numpy as np

import pandas as pd

# ConoBot imports
from middleware.workflow import ConoBotWorkflow as workflow
from frontend.setup_manager import SetupManager

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


class ConfigManager:
	"""Handles configuration loading and saving for ConoBot."""

	# ✅ Define CONFIG_FILE as a class attribute
	CONFIG_FILE = os.path.expanduser("~/.cono_bot_config.json")

	@staticmethod
	def load_config():
		"""Loads user configuration from file with error handling."""
		config = {}

		try:
			if os.path.exists(ConfigManager.CONFIG_FILE):  # ✅ Use class attribute
				with open(ConfigManager.CONFIG_FILE, "r") as file:
					config = json.load(file)
					if not isinstance(config, dict):  # Ensure it's a dictionary
						raise ValueError("Invalid config format")
		except (json.JSONDecodeError, IOError, ValueError) as e:
			logging.error(f"❌ Error reading config file: {e}")

		return config  # Ensuring a dictionary is always returned

	@staticmethod
	def save_config(config):
		"""Saves user configuration to file safely."""
		if not isinstance(config, dict):
			logging.error("❌ Invalid config data: Expected a dictionary")
			QMessageBox.warning(None, "Save Error", "Configuration data is invalid. Expected a dictionary.")
			return

		try:
			with open(ConfigManager.CONFIG_FILE, "w") as file:  # ✅ Use class attribute
				json.dump(config, file, indent=4)
			logging.info("✅ Configuration saved successfully.")
		except (IOError, json.JSONDecodeError) as e:
			logging.error(f"❌ Failed to save config file: {str(e)}")
			QMessageBox.warning(None, "Save Error", "Failed to save configuration. Please check file permissions.")

		# ✅ Close Setup Window and Restart Main UI
		setup_window.close()
		parent.config = ConfigManager.load_config()
		parent.api_key = parent.config.get("full_api_key", "")
		parent.organization_id = parent.config.get("full_organization_id", None)

		# ✅ Ensure UI reloads properly
		if hasattr(parent, "initialize_main_ui") and callable(parent.initialize_main_ui):
			parent.initialize_main_ui()
		else:
			logging.error("⚠ 'initialize_main_ui' function missing in parent object.")

class UDS:

	def __init__(self):
	# Auto-save and backup file paths
		AUTO_SAVE_FILE = "autosave.json"
		BACKUP_FILE = "backup_autosave.json"
		self.AUTO_SAVE_FILE = AUTO_SAVE_FILE
		self.BACKUP_FILE = BACKUP_FILE
		self.utilities_dir = self.conoutils.utilities_dir
		self.workflow = workflow ()

	def enable_auto_save(self):
		"""Enables auto-save functionality if configured in settings."""
		if hasattr(self, 'save_autosave') and callable(self.save_autosave):
			self.autosave_timer = QTimer(self)
			self.autosave_timer.timeout.connect(self.save_autosave)
			self.autosave_timer.start(1000)  # ✅ Auto-save every single second
			logging.info("✅ Auto-save enabled.")
		else:
			logging.error("⚠ save_autosave function is missing. Auto-save will not work.")	
	
	def save_autosave(self):
		"""
		Automatically saves the current state of the assay to prevent data loss.
		- Saves current assay data, parameters, and processing state
		- Creates backup of previous autosave before overwriting
		- Handles errors gracefully to prevent disruption to the user
		"""
		try:
			# Skip autosave if no assay is active
			if not hasattr(self, 'assay_name') or not self.assay_name:
				return

			self.auto_save_path = os.path.join(self.utilities_dir, self.AUTO_SAVE_FILE)
			self.backup_path = os.path.join(self.utilities_dir, self.BACKUP_FILE)

			# Backup previous autosave if it exists
			if os.path.exists(self.auto_save_path):
				try:
					shutil.copy2(self.auto_save_path, self.backup_path)
				except Exception as e:
					logging.warning(f"⚠ Failed to create backup of autosave: {str(e)}")

			# Collect current state data
			autosave_data = {}

			# Load existing autosave data if available
			if os.path.exists(self.auto_save_path):
				try:
					with open(self.auto_save_path, "r") as file:
						autosave_data = json.load(file)
				except json.JSONDecodeError:
					logging.warning("⚠ Corrupted autosave file detected. Creating new autosave.")
					autosave_data = {}

			# Prepare data for current assay
			assay_data = {
				"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
				"current_step": self.workflow.current_step,
			}

			# Save step-specific data
			if workflow.current_step == 1:  # Smoothing step
				# Save smoothing parameters
				if hasattr(self, 'savgol_checkbox') and self.savgol_checkbox.isChecked():
					assay_data["savgol"] = {
						"enabled": True,
						"window_size": self.savgol_window_size.value() if hasattr(self, 'savgol_window_size') else None,
						"polyorder": self.savgol_polyorder.value() if hasattr(self, 'savgol_polyorder') else None
					}
				
				if hasattr(self, 'cubic_spline_checkbox') and self.cubic_spline_checkbox.isChecked():
					assay_data["cubic_spline"] = {"enabled": True}
					
				if hasattr(self, 'ft_lowpass_checkbox') and self.ft_lowpass_checkbox.isChecked():
					assay_data["ft_lowpass"] = {"enabled": True}
			
			# Save wavelength and data arrays if they exist
			if hasattr(self, 'wavelengths') and hasattr(self, 'data'):
				if isinstance(self.wavelengths, np.ndarray) and len(self.wavelengths) > 0:
					assay_data["wavelengths"] = self.wavelengths.tolist()
				if isinstance(self.data, np.ndarray) and len(self.data) > 0:
					assay_data["data"] = self.data.tolist()

			# Add or update the current assay in the autosave data
			autosave_data[self.assay_name] = assay_data

			# Write autosave data to file
			with open(self.AUTO_SAVE_FILE, "w") as file:
				json.dump(autosave_data, file, indent=4)

			logging.debug(f"✅ Autosave completed for assay: {self.assay_name}")

		except Exception as e:
			# Log error but don't disrupt user experience
			logging.error(f"❌ Autosave failed: {str(e)}", exc_info=True)
	
	def get_saved_assays(self):
		"""Retrieve saved assays from storage, ensuring a valid list of assay names."""
		assays_path = os.path.join(self.data_directory, "assays")

		# ✅ Ensure the directory exists
		os.makedirs(assays_path, exist_ok=True)

		# ✅ Retrieve only valid assay files (CSV)
		assay_files = [
			f[:-4] for f in os.listdir(assays_path)
			if f.endswith(".csv") and os.path.isfile(os.path.join(assays_path, f))
		]

		return sorted(assay_files)  # ✅ Sort for consistent display

	def create_assay(self, assay_name, image_path):
		"""Create a new assay and store the chosen thumbnail image."""
		
		logging.info(f"🆕 Creating new assay: {assay_name}")

		assays_path = os.path.join(self.data_directory, "assays")
		os.makedirs(assays_path, exist_ok=True)

		assay_file = os.path.join(assays_path, f"{assay_name}.csv")
		if not os.path.exists(assay_file):
			pd.DataFrame(columns=["Wavelength (nm)", "Absorbance"]).to_csv(assay_file, index=False)

		# ✅ Store Assay Metadata (Including Thumbnail Image)
		metadata_file = os.path.join(self.data_directory, "assays_metadata.json")

		# ✅ Ensure metadata is a valid dictionary before writing
		metadata = {}
		if os.path.exists(metadata_file):
			try:
				with open(metadata_file, "r") as file:
					metadata = json.load(file)
					if not isinstance(metadata, dict):
						raise ValueError("Metadata file is corrupted. Resetting.")
			except (json.JSONDecodeError, ValueError) as e:
				logging.error(f"❌ Failed to read metadata file: {e}")
				metadata = {}

		metadata[assay_name] = {"thumbnail": image_path}

		try:
			with open(metadata_file, "w") as file:
				json.dump(metadata, file, indent=4)
			logging.info(f"✅ Assay metadata updated with thumbnail image: {image_path}")
		except IOError as e:
			logging.error(f"❌ Error saving metadata: {str(e)}")

		# ✅ Open the newly created assay
		self.open_assay(assay_name)

	def delete_assay(self, assay_name):
		"""
		Deletes an assay and its associated data from storage, ensuring UI updates properly.
		"""

		# ✅ Ensure deletion only occurs in Step 0
		if self.current_step != 0:
			logging.warning("⚠ Assay deletion attempted outside Step 0. Ignoring.")
			return

		# ✅ Confirm deletion with the user
		reply = QMessageBox.question(
			self, "Delete Assay",
			f"Are you sure you want to permanently delete the assay '{assay_name}'?",
			QMessageBox.Yes | QMessageBox.No, QMessageBox.No
		)

		if reply == QMessageBox.Yes:
			assay_file = os.path.join(self.data_directory, "assays", f"{assay_name}.csv")
			metadata_file = os.path.join(self.data_directory, "assays_metadata.json")

			# ✅ Ensure the file exists before attempting deletion
			if not os.path.exists(assay_file):
				QMessageBox.warning(self, "Error", f"Assay '{assay_name}' not found in storage.")
				return

			try:
				os.remove(assay_file)
				logging.info(f"✅ Assay '{assay_name}' deleted successfully.")

				# ✅ Remove assay from metadata
				if os.path.exists(metadata_file):
					with open(metadata_file, "r") as file:
						metadata = json.load(file)

					if assay_name in metadata:
						del metadata[assay_name]

					with open(metadata_file, "w") as file:
						json.dump(metadata, file, indent=4)

				# ✅ Remove assay from findings if it exists
				self.delete_finding(assay_name)

				# ✅ Refresh UI after deletion
				if hasattr(self, 'load_assays') and callable(self.load_assays):
					self.load_assays()

				QMessageBox.information(self, "Deleted", f"Assay '{assay_name}' has been permanently removed.")

			except OSError as e:
				logging.error(f"❌ Error deleting assay '{assay_name}': {str(e)}")
				QMessageBox.critical(self, "Error", f"Failed to delete assay '{assay_name}'. Check file permissions.")

	def delete_finding(self, assay_name):
		"""Deletes an assay from My Findings."""
		if not hasattr(self, 'data_directory'):
			return

		findings_file = os.path.join(self.data_directory, "autosave.json")
		if not os.path.exists(findings_file):
			return

		try:
			with open(findings_file, "r") as file:
				findings = json.load(file)

			if assay_name in findings:
				del findings[assay_name]
				with open(findings_file, "w") as file:
					json.dump(findings, file, indent=4)

			logging.info(f"✅ Finding '{assay_name}' deleted successfully.")

			# ✅ Refresh UI after deletion
			if hasattr(self, 'load_assays') and callable(self.load_assays):
				self.load_assays()

		except Exception as e:
			logging.error(f"❌ Error deleting finding '{assay_name}': {str(e)}")
			QMessageBox.critical(self, "Error", f"Failed to delete finding '{assay_name}'. Check file permissions.")

		# ✅ Ensure UI is updated properly
		if hasattr(self, "central_widget") and isinstance(self.central_widget, QWidget):
			self.central_widget.repaint()  # ✅ Forces UI refresh to prevent visual glitches

		logging.info("✅ All unnecessary UI elements hidden for smooth transition.")

	def save_assay_to_findings(self):
		"""Saves the Step 5 frameworks results to 'My Findings' for future reference."""

		if not self.assay_name:
			QMessageBox.warning(self, "Save Error", "No assay is currently active.")
			return

		try:
			timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			
			# ✅ Create findings directory if it doesn't exist
			findings_dir = os.path.join(self.data_directory, "findings")
			os.makedirs(findings_dir, exist_ok=True)
			
			findings_file = os.path.join(findings_dir, "findings.json")
			
			# ✅ Load existing findings
			findings_data = {}
			if os.path.exists(findings_file):
				with open(findings_file, "r") as file:
					findings_data = json.load(file)

			# ✅ Only save Step 5 framework results
			findings_data[self.assay_name] = {
				"Timestamp": timestamp,
				"final_frameworks": self.final_frameworks if hasattr(self, 'final_frameworks') else [],
				"disulfide_connectivity": self.disulfide_connectivity if hasattr(self, 'disulfide_connectivity') else {},
				"species_matches": self.species_matches if hasattr(self, 'species_matches') else []
			}

			with open(findings_file, "w") as file:
				json.dump(findings_data, file, indent=4)

			logging.info(f"✅ Assay '{self.assay_name}' Step 5 framework results saved to My Findings.")

			QMessageBox.information(self, "Frameworks Saved", 
				"Framework results have been saved to 'My Findings'.\n"
				"You can view all saved frameworks in one place from the 'My Findings' button.")
			
			# ✅ Clean up current assay session and return to home screen
			self.cleanup_assay_session()
			self.reset_to_home()

		except Exception as e:
			logging.error(f"⚠ Error while saving frameworks to findings: {str(e)}")
			QMessageBox.critical(self, "Save Error", "Failed to save framework results.")
