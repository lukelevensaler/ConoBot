# Standard Library Imports
import sys
import os
import logging
import time
import datetime
import shutil

#PDF Processing
import pytesseract
import pdfplumber
import cv2
from pdf2image import convert_from_path

#High-Powered Data Analysis
import pandas as pd  
import numpy as np
from openai import OpenAI
from os.path import exists 

# Scientific Computing & Signal Processing
from scipy.signal import savgol_filter  
from scipy.interpolate import CubicSpline
from lmfit.models import VoigtModel  
from skopt import gp_minimize
from skopt.space import Integer
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from functools import partial
import json

# Bioinformatics
from Bio import SeqIO
import re
import gzip





class ConoBotWorkflow:
	
	"""Handles the step-based logic of an assay and related UI transitions."""
	def get_step_description(self):
		"""Returns a structured description of each step in the workflow."""
		steps = {
			0: "🏠 Main Screen → Select/Create an Assay, Access My Findings & References.",
			1: "📊 Preprocess Smoothing → Applies AI Savitzky-Golay filter if enabled.",
			2: "🔬 AI Cysteine & HRP Deconvolution (350-700 nm) → Background Process with Loading Screen.",
			3: "📑 Display Quantification Results → Shows HRP & Zn(II) cysteine complex outputs, allows user input.",
			4: "🧬 AI Amide Mapping (NIR 700-1020 nm) + ConoServer Matching → Background Process with Loading Screen.",
			5: "✅ Display Filtered Frameworks → Shows Linear Sequence, Disulfide Connectivity, and Species Matches.",
		}
		return steps.get(self.current_step, "🚨 Unknown Step - Workflow Error.")

	def validate_step(self):
		"""Ensures all required fields are correctly filled before proceeding with the workflow."""

		# ✅ Ensure all mandatory inputs are filled
		if not self.require_mandatory_input():
			logging.warning("⚠ Required inputs are missing.")
			return False

		# ✅ Step 2 Validation: Savitzky-Golay Filtering
		if self.current_step == 2:
			if hasattr(self, "savgol_checkbox") and self.savgol_checkbox.isChecked():
				use_bayesian = hasattr(self, 'bayesian_opt_checkbox') and self.bayesian_opt_checkbox.isChecked()

				if not use_bayesian:
					try:
						if hasattr(self, "savgol_window_size") and hasattr(self, "savgol_polyorder"):
							window_size = int(self.savgol_window_size.value())
							poly_order = int(self.savgol_polyorder.value())

							if window_size % 2 == 0 or window_size <= 0:
								raise ValueError("Savitzky-Golay window size must be an odd positive integer.")
							if poly_order >= window_size:
								raise ValueError("Polynomial order must be smaller than window size.")
						else:
							logging.warning("⚠ Savitzky-Golay UI elements are not initialized yet.")
							return False
					except ValueError as e:
						logging.error(f"❌ Savitzky-Golay validation error: {str(e)}")
						QMessageBox.warning(self, "Invalid Input", str(e))
						return False

		# ✅ Progress Bar Validation for Steps 2 and 4
		if self.current_step in [2, 4]:
			if self.progress_bar.value() != 100:  # Check if the single progress bar is at 100
				logging.warning(f"⚠ Progress bar is not complete for Step {self.current_step}.")
				QMessageBox.warning(self, "Incomplete Progress", "Please wait for the progress bar to complete.")
				return False

		# ✅ Step 3 Validation: Amide Mapping Input Check
		if self.current_step == 3:
			required_amide_fields = [
				"cysteine_count", "peptide_count", "termina_count",
				"C_complex_count", "CC_complex_count", "CCC_complex_count"
			]
			amide_inputs_filled = all(bool(self.manual_inputs.get(field)) for field in required_amide_fields)

			if not amide_inputs_filled:
				logging.warning("⚠ Amide Mapping required fields are missing.")
				QMessageBox.warning(self, "Missing Fields", "Please fill out all required fields for Amide Mapping.")
				return False

		# ✅ If everything is valid, enable the `next_button`
		self.next_button.setEnabled(True)
		logging.info(f"✅ Step {self.current_step} validation passed. Next button enabled.")

		return True  # ✅ All validations passed
	
	def require_mandatory_input(self):
		"""Ensures all required fields are filled and valid before allowing the user to proceed."""

		# ✅ Ensure `required_fields` exists and is a dictionary
		if not hasattr(self, "required_fields") or not isinstance(self.required_fields, dict):
			logging.error("❌ 'required_fields' dictionary is missing or not initialized.")
			return False

		missing_fields, invalid_fields = [], []

		for field_name, widget in self.required_fields.items():
			if not widget or not widget.isVisible():  # ✅ Skip non-visible widgets
				continue

			try:
				if isinstance(widget, QLineEdit):
					text_value = widget.text().strip()

					if not text_value:
						missing_fields.append(field_name)  # ✅ Missing input
					elif not text_value.isnumeric():
						invalid_fields.append(field_name)  # ✅ Must be numeric
					else:
						value = int(text_value)
						if value <= 0:
							invalid_fields.append(field_name)  # ✅ Ensure positive values

				elif isinstance(widget, QSpinBox):
					value = widget.value()
					if value <= 0:
						invalid_fields.append(field_name)  # ✅ Must be positive

				elif isinstance(widget, QCheckBox):
					if not widget.isChecked():
						missing_fields.append(field_name)  # ✅ Must be checked

			except Exception as e:
				logging.error(f"❌ Error validating field '{field_name}': {str(e)}")
				invalid_fields.append(field_name)  # ✅ Mark as invalid if an exception occurs

		# ✅ Determine validation status
		is_valid = not (missing_fields or invalid_fields)

		# ✅ Update `next_button` state
		if hasattr(self, "next_button") and isinstance(self.next_button, QPushButton):
			self.next_button.setEnabled(is_valid)

		# ✅ Display warnings only when necessary
		if missing_fields:
			QMessageBox.warning(self, "Missing Data", f"Please fill in: {', '.join(missing_fields)}")

		if invalid_fields:
			QMessageBox.warning(self, "Invalid Input", f"Enter valid positive numbers for: {', '.join(invalid_fields)}")

		return is_valid  # ✅ Returns True if all fields are valid

	def exit_assay(self):
		"""Handles exiting an active assay session safely, ensuring data is saved before returning to the main screen."""

		reply = QMessageBox.question(
			self,
			"Exit Assay",
			"Are you sure you want to exit the assay?\nYour progress will be saved automatically.",
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.No
		)

		if reply == QMessageBox.Yes:
			logging.info("🔄 Exiting assay session, saving progress...")

			# ✅ Save progress before exiting
			if hasattr(self, "save_autosave") and callable(self.save_autosave):
				self.save_autosave()
			else:
				logging.warning("⚠ Autosave function missing! Exiting without saving.")

			# ✅ Cleanup active assay session
			if hasattr(self, "cleanup_assay_session") and callable(self.cleanup_assay_session):
				self.cleanup_assay_session()
			else:
				logging.error("❌ cleanup_assay_session() function is missing!")

			# ✅ Return to Home Screen (Step 0)
			if hasattr(self, "reset_to_home") and callable(self.reset_to_home):
				self.reset_to_home()
				logging.info("✅ UI transitioned back to the main menu.")
			else:
				logging.error("❌ reset_to_home() function is missing!")

		else:
			logging.info("⚠ Assay exit canceled by user.")

	def handle_next_step(self):
		"""
		Handles workflow transitions safely, ensuring correct UI state, preventing duplicate widget creations,
		and maintaining full cohesion with ConoBot's main workflow.
		"""

		# ✅ Prevent transition if setup UI is active
		if hasattr(self, "setup_window") and self.setup_window is not None:
			logging.info("⚠ Setup UI is active, preventing step transition.")
			return

		# ✅ Validate all required fields before proceeding
		if not self.validate_step():
			QMessageBox.warning(self, "Incomplete Data", "Please complete all required fields before proceeding.")
			return  

		# ✅ Step 3 → Step 4: Trigger AI Amide Mapping
		if self.current_step == 3:
			logging.info("✅ Validation successful. Initiating AI Amide Mapping...")
			if hasattr(self, "run_ai_amide_deconvolution") and callable(self.run_ai_amide_deconvolution):
				self.run_ai_amide_deconvolution()
			else:
				logging.error("❌ run_ai_amide_deconvolution() function is missing!")

		# ✅ Move to the next step safely
		self.current_step += 1
		logging.info(f"🔄 User moved to Step {self.current_step}: {self.get_step_description()}")

		# ✅ Ensure UI updates after step transition
		if hasattr(self, "update_ui_on_step_change") and callable(self.update_ui_on_step_change):
			self.update_ui_on_step_change()
		else:
			logging.error("❌ update_ui_on_step_change() function is missing!")

		# Toggle between "Next" and "Finish" based on workflow step
		if self.current_step == 5:
			self.next_button.setVisible(False)
			self.next_button.setEnabled(False)
			self.finish_button.setVisible(True)
			self.finish_button.setEnabled(True)
		
		if 1 <= self.current_step <= 4:
			self.next_button.setVisible(True)
			self.finish_button.setVisible(False)
			self.finish_button.setEnabled(False)

			# Validate the current step
			if self.validate_step():
				# Validation passed, enable the "Next" button
				self.next_button.setEnabled(True)
			else:
				# Validation failed, disable the "Next" button
				self.next_button.setEnabled(False)
		
		if 1 <= self.current_step <= 4:
			self.exit_button.setVisible(True)
			self.exit_button.setEnabled(True)
		else:
			self.exit_button.setVisible(False)
			self.exit_button.setEnabled(False)
		
		# Hide next_button and finish_button when resetting to home screen
		if self.current_step == 0:
			self.next_button.setVisible(False)
			self.next_button.setEnabled(False)
			self.finish_button.setVisible(False)
			self.finish_button.setEnabled(False)
		
		# Hide Progress Bar When It Is Done
		if self.current_step in [2,4]:
			if self.progress_bar.value() == 100:
				self.progress_bar.hide()
				QMessageBox.information(self, "Process Complete", "Process Complete! Click Next to Proceed.")
			else:
				self.progress_bar.show()

		# ✅ Final UI update and logging
		QApplication.processEvents()  # 🔥 Ensures smooth UI transition
		logging.info(f"✅ UI updated for Step {self.current_step}. Next button: {self.next_button.isVisible()}, Finish button: {self.finish_button.isVisible()}")
		
		# Ensure that the exit button only shows when in steps 1 through 4
		if 1 <= self.current_step <= 4:
			self.exit_button.setVisible(True)
			self.exit_button.setEnabled(True)
		else:
			self.exit_button.setVisible(False)
			self.exit_button.setEnabled(False)

	def reset_to_home(self):
		"""Returns to Step 0 (Main Screen) safely, ensuring UI resets properly."""

		# ✅ Reset the workflow step
		self.current_step = 0
		logging.info("🏠 Returning to Home Screen (Step 0).")

		# ✅ Ensure UI updates properly
		if hasattr(self, "update_ui_on_step_change") and callable(self.update_ui_on_step_change):
			self.update_ui_on_step_change()
		else:
			logging.error("❌ update_ui_on_step_change() function is missing!")

		# ✅ Ensure UI transition is smooth
		QApplication.processEvents()  # 🔥 Prevents UI lag

		logging.info("✅ UI successfully reset to Home Screen.")

	def cleanup_assay_session(self):
		"""Safely resets only necessary assay-related variables while keeping UI intact."""

		logging.info("🧹 Cleaning up assay session variables...")

		# ✅ Reset only the essential state variables
		self.assay_name = None

		if hasattr(self, "manual_inputs") and isinstance(self.manual_inputs, dict):
			self.manual_inputs.clear()
		else:
			logging.warning("⚠ manual_inputs dictionary is missing or corrupted. Resetting to empty dictionary.")
			self.manual_inputs = {}

		self.current_step = 0

		if hasattr(self, "deconvolution_results") and isinstance(self.deconvolution_results, dict):
			self.deconvolution_results.clear()
		else:
			logging.warning("⚠ deconvolution_results dictionary is missing or corrupted. Resetting to empty dictionary.")
			self.deconvolution_results = {}

		if hasattr(self, "amide_mapping_results") and isinstance(self.amide_mapping_results, dict):
			self.amide_mapping_results.clear()
		else:
			logging.warning("⚠ amide_mapping_results dictionary is missing or corrupted. Resetting to empty dictionary.")
			self.amide_mapping_results = {}

		# ✅ UI remains intact, no unnecessary resets
		logging.info("✅ Cleanup complete. UI remains intact.")

	def update_ui_on_step_change(self):
		"""Ensures UI components update correctly when transitioning between steps."""

		logging.info(f"🔹 Updating UI for Step {self.current_step}...")

		if not hasattr(self, "main_layout") or not isinstance(self.main_layout, QVBoxLayout):
			logging.error("❌ 'main_layout' is missing or not properly initialized. Cannot update UI.")
			return

		# Safely clear main layout to prevent C++ deletion errors
		while self.main_layout.count():
			item = self.main_layout.takeAt(0)
			if item.widget():
				item.widget().setParent(None)  # Detach widget from parent
			elif item.layout():
				# Recursively clear child layouts
				self.clear_layout(item.layout())
				item.layout().setParent(None)  # Detach layout

		# Add the appropriate widgets for the current step
		if self.current_step == 0:
			self.main_layout.addWidget(self.home_screen)
		elif self.current_step == 1:
			self.main_layout.addWidget(self.setup_step_1_ui)
		elif self.current_step == 2:
			self.main_layout.addWidget(self.progress_bar_container)
		elif self.current_step == 3:
			self.main_layout.addWidget(self.step3_layout)
		elif self.current_step == 4:
			self.main_layout.addWidget(self.progress_bar_container)
		elif self.current_step == 5:
			self.main_layout.addWidget(self.final_screen)

		logging.info(f"✅ UI successfully updated to Step {self.current_step}.")

	def clear_layout(self, layout):
		"""Recursively clear a layout and its child layouts."""
		while layout.count():
			item = layout.takeAt(0)
			if item.widget():
				item.widget().setParent(None)  # Detach widget from parent
			elif item.layout():
				self.clear_layout(item.layout())
				item.layout().setParent(None)  # Detach layout


class ConoBotLogic:

	"""Handles the backend logic for the ConoBot application, including data processing and AI interactions."""

	def download_smoothed_data(self):
		"""
		Allows scientists to download the smoothed spectral data as a CSV file.
		- Validates that data has been loaded and smoothing has been applied
		- Exports the current smoothed data with original wavelengths
		- Includes metadata about smoothing parameters used
		- Provides user feedback on success/failure
		"""
		try:
			# Validate step - ensure we're in the right processing stage
			if self.current_step != 1:
				QMessageBox.warning(self, "Invalid Step", "Data download is only available during the preprocessing step.")
				return
				
			# Validate that CSV data has been loaded
			if not hasattr(self, 'csv_data') or self.csv_data is None or self.csv_data.empty:
				QMessageBox.warning(self, "No Data", "Please load a CSV file before attempting to download smoothed data.")
				return
				
			# Validate that at least one smoothing method has been applied
			cubic_spline_applied = hasattr(self, 'cubic_spline_checkbox') and self.cubic_spline_checkbox.isChecked()
			ft_lowpass_applied = hasattr(self, 'ft_lowpass_checkbox') and self.ft_lowpass_checkbox.isChecked()
			savgol_applied = hasattr(self, 'savgol_checkbox') and self.savgol_checkbox.isChecked()
			
			if not (cubic_spline_applied or ft_lowpass_applied or savgol_applied):
				response = QMessageBox.question(
					self, 
					"No Smoothing Applied", 
					"No smoothing has been applied to the data. Do you want to download the original data instead?",
					QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
				)
				if response == QMessageBox.StandardButton.No:
					return
			# Get save location from user
			file_path, _ = QFileDialog.getSaveFileName(
				self,
				"Save Spectral Data",
				os.path.expanduser("~/spectral_data.csv"),
				"CSV Files (*.csv)"
			)
			
			if not file_path:  # User canceled
				return
				
			# Create DataFrame with data
			if hasattr(self, 'data') and self.data is not None and len(self.data) > 0:
				# Use smoothed data if available
				data_to_save = pd.DataFrame({
					"Wavelength (nm)": self.wavelengths,
					"Absorbance": self.data
				})
				is_smoothed = True
			else:
				# Fall back to original data if no smoothed data
				data_to_save = self.csv_data.copy()
				is_smoothed = False
				
			# Add metadata as comments in the CSV header
			metadata = [
				"# ConoBot Spectral Data Export",
				f"# Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
			]
			
			# Add smoothing parameters if Savitzky-Golay was used
			if is_smoothed and hasattr(self, 'savgol_checkbox') and self.savgol_checkbox.isChecked():
				metadata.extend([
					f"# Smoothing Method: Savitzky-Golay Filter",
					f"# Window Size: {self.savgol_window_size.value()}",
					f"# Polynomial Order: {self.savgol_polyorder.value()}"
				])
			else:
				metadata.append("# Smoothing Method: None (Original Data)")
				
			# Write to CSV with metadata
			with open(file_path, 'w') as f:
				for line in metadata:
					f.write(line + '\n')
				data_to_save.to_csv(f, index=False)
				
			logging.info(f"✅ Successfully saved {'smoothed' if is_smoothed else 'original'} data to {file_path}")
			QMessageBox.information(
				self, 
				"Success", 
				f"{'Smoothed' if is_smoothed else 'Original'} data saved to:\n{file_path}"
			)
			
		except Exception as e:
			logging.error(f"❌ Error saving data: {str(e)}")
			QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")

	def ai_deconvolution(self):
		"""
		Runs AI-driven cysteine dentate complex and HRP (Horseradish Peroxidase) quantification using OpenAI API.
		- Analyzes deconvoluted spectral data.
		- Extracts context from cysteine dentate PDFs.
		- Uses AI to quantify HRP and Zn-cysteine dentate complexes.
		- Updates UI with results.
		"""

		# ✅ Ensure this only runs during Step 2 (AI Deconvolution)
		if not hasattr(self, 'current_step'):
			logging.error("❌ `current_step` is not defined. Cannot run deconvolution.")
			return

		if self.current_step != 2:
			logging.warning("⚠ Deconvolution attempted outside Step 2. Ignoring.")
			return

		if not hasattr(self, 'csv_data') or self.csv_data.empty:
			QMessageBox.critical(self, "Error", "No spectral data available for deconvolution. Please load a CSV first.")
			return

		# ✅ Now use self.csv_data["Wavelength (nm)"] and self.csv_data["Absorbance"]
		wavelengths = self.csv_data["Wavelength (nm)"].values
		absorbance_values = self.csv_data["Absorbance"].values

		logging.info("✅ AI Deconvolution using loaded CSV data.")

		try:
			logging.info("🔹 Running AI-driven cysteine dentate deconvolution...")

			self.progress_bar.setVisible(True)
			self.progress_bar.setValue(0)
			self.repaint()
			QApplication.processEvents()  # ✅ UI remains responsive

			# ✅ Ensure Spectral Data Exists
			if not hasattr(self, 'wavelengths') or not hasattr(self, 'data'):
				raise ValueError("❌ No spectral data available for deconvolution.")

			# ✅ Restrict Analysis to 350-700 nm (NUV-Vis range for HRP Soret Band & Zn-Cysteine Complexes)
			valid_indices = (self.wavelengths >= 350) & (self.wavelengths <= 700)
			wavelengths_subset = self.wavelengths[valid_indices]
			data_subset = self.data[valid_indices]

			if data_subset.size == 0:
				raise ValueError("❌ No valid spectral data in the 350-700 nm range.")

			# ✅ Substep 1: Perform Deconvolution with Voigt Model + Nonlinear Least Squares
			logging.info("🔹 Performing Voigt Model Deconvolution on HRP & Cysteine Complexes...")
			self.progress_bar.setValue(25)
			self.repaint()
			QApplication.processEvents()  # ✅ UI remains responsive

			model = VoigtModel()
			params = model.make_params(amplitude=1, center=550, sigma=10, gamma=5)
			result = model.fit(data_subset, params, x=wavelengths_subset)

			deconvoluted_data = result.best_values
			logging.info("✅ Voigt Model Deconvolution Complete.")
			self.progress_bar.setValue(50)
			self.repaint()
			QApplication.processEvents()  # ✅ UI remains responsive

			# ✅ Substep 2: Extract Context from Cysteine Dentate PDFs
			logging.info("🔹 Extracting context from cysteine dentate PDFs...")
			pdf_files = [
				"data/cysteine_dentate/penner-hahn-et-al-2001-zinc-thiolate-intermediate-in-catalysis-of-methyl-group-transfer-in-methanosarcina-barkeri.pdf",
				"data/cysteine_dentate/Metal_Binding_Ability_of_Small_Peptides_Containing.pdf",
				"data/cysteine_dentate/krizek-et-al-2002-ligand-variation-and-metal-ion-binding-specificity-in-zinc-finger-peptides.pdf",
				"data/cysteine_dentate/imanishi-et-al-2012-zn(ii)-binding-and-dna-binding-properties-of-ligand-substituted-cxhh-type-zinc-finger-proteins.pdf"
			]
			dentate_pdf_text = "\n".join([self.extract_text_from_pdf(pdf) for pdf in pdf_files if os.path.exists(pdf)])

			logging.info("✅ PDF Extraction Complete.")
			self.progress_bar.setValue(75)
			self.repaint()
			QApplication.processEvents()  # ✅ UI remains responsive

			# ✅ Step 3: Run AI Deconvolution
			logging.info("🔹 Sending AI Request for HRP & Cysteine Quantification...")

			ai_prompt = [
				{
					"role": "system",
					"content": (
						"Use your common knowledge, cysteine dentate context PDFs, the deconvoluted NUV-Vis and "
						"advanced spectral calculations (such as the Beer-Lambert Law) to quantify the total number "
						"of oxidized Type IV Horseradish Peroxidase (HRP) (44,000 kDa) (given by Soret Band and "
						"(Zinc II)- (thiol cysteine side chain) coordination complexes, including Zn-single cysteine (C) "
						"complexes, Zinc-double cysteine (CC) complexes, and the rare Zinc-triple cysteine (CCC) complexes "
						"in the cuvette assay environment with a path length of 1 cm. "
						"Within the context PDFs, you must focus exclusively on Zinc coordination, and there may be information "
						"about histidine-Zinc complexes that should be always treated as irrelevant and only cysteine context is "
						"gleaned for your usage (e.g., Zn-CHC complex spectral characteristics described in a PDF are just treated "
						"as context for the spectral characteristics of a Zn-CC complex). "
						"You are an expert-level, exact, ultra-persistent, ultra-precise, ultra-analytical, and ultra-accurate tool "
						"for HRP and Zinc-cysteine dentate quantification, but don't be erroneous if analysis fails, just error instead."
					),
				},
				{
					"role": "user",
					"content": (
						f"Extracted PDF Text:\n{dentate_pdf_text}\n\n"
						f"Spectral Data (350-700 nm): {data_subset.tolist()}\n"
						f"Voigt Fit Results: {json.dumps(deconvoluted_data)}"
					),
				},
			]

			response = self.client.chat.completions.create(
				model="gpt-4o",
				temperature=0,
				messages=ai_prompt,
				max_tokens=10000,
			)

			if not response or "choices" not in response or not response["choices"]:
				raise ValueError("AI response is empty or improperly formatted.")

			self.deconvolution_results = json.loads(response["choices"][0]["message"]["content"])

			logging.info("✅ AI Deconvolution Successfully Completed.")
			self.progress_bar.setValue(100)
			self.repaint()
			QApplication.processEvents()

			# ✅ Step 4: Transition to Step 3 (Amide Mapping Input)
			logging.info("🔹 Transitioning to Step 3...")
			self.current_step = 3
			self.update_ui_on_step_change()

			# ✅ Display Deconvolution Results
			self.display_quantification_results()

		except Exception as e:
			logging.error(f"❌ Error during AI deconvolution: {str(e)}", exc_info=True)
			QMessageBox.critical(self, "Error", f"AI deconvolution failed: {str(e)}", exc_info=True)

		finally:
			self.progress_bar.setVisible(False)
			self.repaint()
			QApplication.processEvents()  # ✅ Ensure UI remains responsive

	def analyze_conoserver(self):
		"""Extracts species associations, citations, and gene superfamilies for AI-mapped frameworks while ensuring synthetic peptides are excluded."""
		
		conoserver_path = "data/framework_knowledge/conoserver.fa.gz"

		if not exists(conoserver_path):
			logging.error("❌ ConoServer database not found! Framework analysis will be incomplete.")
			return {"status": "error", "message": "ConoServer database missing."}

		matched_entries = []

		try:
			with gzip.open(conoserver_path, "rt") as handle:
				for record in SeqIO.parse(handle, "fasta"):
					description = record.description
					sequence = str(record.seq)

					# ✅ Ensure amide mapping results exist
					if hasattr(self, 'amide_mapping_results') and 'linear_sequence' in self.amide_mapping_results:
						mapped_sequence = self.amide_mapping_results['linear_sequence']

						# ✅ Check for synthetic peptides (Exclude if identified as synthetic)
						if "synthetic" in description.lower() or "artificial" in description.lower():
							logging.info(f"❌ Synthetic peptide excluded: {description}")
							continue  # Skip synthetic peptides

						# ✅ Check if mapped sequence exists in ConoServer sequence database
						if mapped_sequence in sequence:
							entry = {
								"species": description.split("|")[1],  # Extract species name
								"citation": description.split("|")[-1],  # Extract citation
								"sequence": sequence
							}

							# ✅ Extract Pharmacological Class (Greek letters) & Gene Superfamily (Roman letters)
							class_match = re.search(r"([Α-Ωα-ω])", description)  # Greek letters
							family_match = re.search(r"([IVXLCDM]+)", description)  # Roman numerals

							entry["pharmacological_class"] = class_match.group(1) if class_match else "Unknown"
							entry["gene_superfamily"] = family_match.group(1) if family_match else "Unknown"

							matched_entries.append(entry)

			# ✅ Handle cases where no valid matches are found (i.e., no natural peptide matches)
			if not matched_entries:
				logging.info("✅ ConoServer analysis complete. No natural matches found → Novel framework.")
				return {
					"status": "novel", 
					"framework_match": "Novel!", 
					"species": [], 
					"references": [], 
					"pharmacological_classes": [], 
					"gene_superfamilies": []
				}

			return {
				"status": "matched",
				"framework_match": matched_entries[0]["sequence"],
				"species": list(set(entry["species"] for entry in matched_entries)),
				"references": list(set(entry["citation"] for entry in matched_entries)),
				"pharmacological_classes": list(set(entry["pharmacological_class"] for entry in matched_entries)),
				"gene_superfamilies": list(set(entry["gene_superfamily"] for entry in matched_entries))
			}

		except Exception as e:
			logging.error(f"❌ Error analyzing ConoServer: {str(e)}", exc_info=True)
			return {"status": "error", "message": "Failed to analyze ConoServer."}

	def run_ai_amide_deconvolution(self):
		"""Runs AI-driven amide mapping, NIR deconvolution, and ConoServer analysis in one controlled step."""

		if self.current_step != 4:
			logging.warning("⚠ AI Amide Mapping attempted outside Step 4. Ignoring.")
			return

		if not self.client:
			logging.warning("⚠ OpenAI client is uninitialized. AI features will not work.")
			QMessageBox.warning(self, "AI Unavailable", "OpenAI API key is missing. AI-driven features will not work.")
			return

		if not hasattr(self, 'csv_data') or self.csv_data.empty:
			QMessageBox.critical(self, "Error", "No spectral data available for deconvolution. Please load a CSV first.")
			return

		try:
			logging.info("🔹 Running AI-driven amide mapping step...")

			user_context = self.amide_context_input.toPlainText().strip()
			if not user_context:
				raise ValueError("User must provide context for AI amide mapping.")

			# ✅ Ensure Loading Label is Set **After Initialization**
			self.loading_label.setText("Initializing Amide Mapping...")
			self.loading_label.setVisible(True)
			self.progress_bar.setVisible(True)
			self.progress_bar.setValue(10)
			self.repaint()
			QApplication.processEvents()

			# ✅ AI Processing...
			ai_prompt = [
				{"role": "system", "content": 
					"Use amide mapping conext PDFs, advanced spectral calculations (including the Beer-Lambert Law), "
					"your common knowledge, conoserver, and deconvoluted NIR spectral data to "
					"obtain an advanced dataset on the amide-exclusive structural arrangments (such as modified residues indicating cysteine complexes, termina, and bond backbones) "
					"accounting for all of the individual peptides in the assay based on inputted values for the total number of different "
					"types of linearly adjacent cysteine complexes (which will cause slightly different structural modifications of residues) (C, CC, and CCC) (keep in mind: primary structure), "
					"number of peptides total, the number of termina "
					"(assume both termina are amidated), and the number of cysteine residues total present in the 1 mL "
					"cuvette assay environment with a path length of 1 cm. You are an expert-level, exact, ultra-persistent, ultra-precise, ultra-analytical, and ultra-accurate tool for "
					"amide structural insights dataset (quantitative) compiling, but don't be erroneous if analysis fails, just error instead."},
				{"role": "user", "content": f"User Context:\n{user_context}"}
			]

			response = self.client.chat.completions.create(
				model="gpt-4o",
				temperature=0,
				messages=ai_prompt,
				max_tokens=10000
			)

			if not response or "choices" not in response or not response["choices"]:
				raise ValueError("AI response is empty or improperly formatted.")

			self.amide_mapping_results = json.loads(response["choices"][0]["message"]["content"])

			logging.info("✅ AI Amide Mapping completed successfully.")
			self.progress_bar.setValue(100)
			self.loading_label.setText("Amide Mapping Complete.")

			QApplication.processEvents()  # ✅ UI remains responsive

			# ✅ Move to Final UI Update
			self.display_filtered_frameworks()

		except Exception as e:
			logging.error(f"❌ Error during amide mapping: {str(e)}", exc_info=True)
			QMessageBox.critical(self, "Error", f"Amide mapping failed: {str(e)}", exc_info=True)

		finally:
			self.loading_label.setVisible(False)
			self.progress_bar.setVisible(False)
			self.repaint()
			QApplication.processEvents()  # ✅ UI remains responsive

	def ai_amide_mapping(self):
		"""Uses AI to map amide structures in the Near Infrared wavelengths (700-1020 nm)."""

		if not self.client:
			logging.warning("⚠ OpenAI client is uninitialized. AI features will not work.")
			QMessageBox.warning(self, "AI Unavailable", "OpenAI API key is missing. AI-driven features will not work.")
			return

		if not hasattr(self, 'wavelengths') or not hasattr(self, 'data'):
			logging.error("Wavelengths or spectral data missing for amide mapping.")
			QMessageBox.critical(self, "Error", "No spectral data available for amide mapping.")
			return

		# ✅ Restrict processing to NIR range (700-1020 nm)
		nir_indices = (self.wavelengths >= 700) & (self.wavelengths <= 1020)
		self.wavelengths = self.wavelengths[nir_indices]
		self.data = self.data[nir_indices]

		if self.data.empty:
			logging.error("No data available in the 700-1020 nm range for amide mapping.")
			QMessageBox.critical(self, "Error", "No valid spectral data in the required wavelength range.")
			return

		amide_pdf_texts = "\n".join([
			self.extract_text_from_pdf(pdf) for pdf in [
			"data/amide_mapping/0470027320_Spectra–_Structure_Correlations_in_the_Near‐Infrared.pdf"
			] if os.path.exists(pdf)
		])

		ai_prompt = [
			{"role": "system", "content": 
				"Use the amide mapping PDF, the NIR deconvolution dataset results, and your common knowledge "
				"to determine cysteine linear frameworks with advanced prescision. For NIR deconvolution data, analyze for bond backbones, termini (both termina are amidated), and, especially,"
				"significant modifications to amino acids (where different cysteine arrangments like C, CC, or (rare) CCC are located, which"
				"you will differentiate from each other to help you successfully identify and quantify the abundance (given be number of peptides with each identifed framework"
				"of cysteine linear (keep in mind: primary sequnece) frameworks) alongside the provided data."
				"You are an expert-level, exact, ultra-persistent, ultra-precise, ultra-analytical, and ultra-accurate tool for"
				"individual peptide-sensitive amide mapping, but dont be erroneous if analysis fails, just error instead."},
			{"role": "user", "content": 
				f"Extracted PDF Text:\n{amide_pdf_texts}\n\n"
				f"NIR Spectral Data (700-1020nm): {self.data.tolist()}"}
		]

		max_retries = 3
		delay = 2

		for attempt in range(max_retries):
			try:
				self.loading_screen.setVisible(True)
				self.progress_bar.setVisible(True)
				self.progress_bar.setValue(25)
				self.loading_label.setText("Running AI Amide Mapping...")
				self.repaint()
				QApplication.processEvents()  # ✅ Ensure UI remains responsive

				response = self.client.chat.completions.create(
					model="gpt-4o",
					temperature=0,
					messages=ai_prompt,
					max_tokens=10000
				)

				self.progress_bar.setValue(75)
				self.loading_label.setText("Processing AI Results...")
				self.repaint()
				QApplication.processEvents()  # ✅ Ensure UI remains responsive

				content = response.choices[0].message.content.strip()
				self.amide_mapping_results = json.loads(content)

				logging.info("✅ AI Amide Mapping completed successfully.")
				self.progress_bar.setValue(100)
				self.loading_label.setText("Amide Mapping Complete.")
				QApplication.processEvents()  # ✅ Ensure UI remains responsive
				return

			except json.JSONDecodeError:
				logging.error(f"AI returned invalid JSON response. Response: {content}")
				QMessageBox.critical(self, "Error", "Invalid AI response. Check logs.")
				break

			except Exception as e:
				logging.error(f"AI Amide Mapping failed (Attempt {attempt+1}/{max_retries}): {str(e)}")
				if attempt < max_retries - 1:
					time.sleep(delay)
					delay *= 2
				else:
					QMessageBox.critical(self, "Error", f"AI Amide Mapping failed after {max_retries} attempts. Check logs.")

			finally:
				self.loading_screen.setVisible(False)
				self.progress_bar.setVisible(False)
				self.repaint()
				QApplication.processEvents()  # ✅ Ensure UI remains responsive
		
	def load_csv(self):
		"""
		Loads a CSV file, detects and skips a title row if necessary, and makes it accessible across all steps.
		"""

		file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")

		if not file_path:
			logging.warning("⚠ No file selected.")
			return  # ✅ User canceled file selection

		try:
			# ✅ Show loading screen if file is large
			self.loading_screen.setVisible(True)
			self.loading_label.setText("Loading CSV Data...")
			self.progress_bar.setVisible(True)
			self.progress_bar.setValue(10)
			self.repaint()

			# ✅ Load CSV without assuming a header
			df = pd.read_csv(file_path, header=None)

			# ✅ Detect & Skip Title Row (Non-numeric first row)
			first_row = df.iloc[0]
			if not first_row.apply(lambda x: str(x).replace('.', '', 1).isdigit()).all():
				logging.info("📝 Detected a potential title row. Skipping first row.")
				df = df.iloc[1:].reset_index(drop=True)

			# ✅ Ensure at least two columns exist (Wavelength, Absorbance)
			if df.shape[1] < 2:
				QMessageBox.critical(self, "Error", "CSV must have at least two columns (X: Wavelength, Y: Absorbance).")
				return

			self.progress_bar.setValue(40)

			# ✅ Assign correct column names
			df.columns = ["Wavelength (nm)", "Absorbance"]

			# ✅ Convert to numeric and filter the spectral range
			df["Wavelength (nm)"] = pd.to_numeric(df["Wavelength (nm)"], errors="coerce")
			df["Absorbance"] = pd.to_numeric(df["Absorbance"], errors="coerce")

			# ✅ Ensure data is within the expected spectral range (350-1020 nm)
			df = df[(df["Wavelength (nm)"] >= 350) & (df["Wavelength (nm)"] <= 1020)]
			if df.empty:
				QMessageBox.warning(self, "Warning", "⚠ No valid spectral data in the range 350-1020 nm.")
				return

			self.progress_bar.setValue(70)

			# ✅ Store cleaned data globally for all steps
			self.csv_data = df

			# ✅ Ensure the data is available in all steps
			self.wavelengths = df["Wavelength (nm)"].values
			self.absorbance_values = df["Absorbance"].values

			logging.info("✅ CSV data successfully loaded and will be available for all steps.")

			# ✅ Ensure UI updates smoothly
			if self.current_step == 1:
				self.update_graph_view(self.csv_data)
				self.graph_container.setVisible(True)

			self.next_button.setEnabled(True)

			self.progress_bar.setValue(100)

		except Exception as e:
			logging.error(f"❌ Failed to process CSV data: {e}")
			QMessageBox.critical(self, "CSV Error", "⚠ Invalid CSV data format.")

		finally:
			# ✅ Hide loading screen when done
			self.loading_screen.setVisible(False)
			self.progress_bar.setVisible(False)
			self.repaint()
			QApplication.processEvents()  # ✅ Ensure UI updates smoothly
		
	def update_graph_view(self, dataframe):
		"""
		Updates the Matplotlib graph during the spectral smoothing step only.
		Ensures graph UI does not display in any other steps.
		"""

		# ✅ Ensure we are in Step 1 before updating the graph
		if self.current_step != 1:
			logging.warning("⚠ Graph update skipped: Not in preprocessing step.")
			return

		if dataframe is None or dataframe.empty:
			logging.warning("⚠ No data available for visualization.")
			QMessageBox.warning(self, "No Data", "No valid spectral data available for visualization.")
			return

		if "Wavelength (nm)" not in dataframe.columns or "Absorbance" not in dataframe.columns:
			logging.error("❌ Missing required columns: 'Wavelength (nm)' and 'Absorbance'.")
			QMessageBox.critical(self, "Error", "CSV must contain 'Wavelength (nm)' as X-axis and 'Absorbance' as Y-axis.")
			return

		if not hasattr(self, 'ax') or not hasattr(self, 'canvas'):
			logging.error("❌ Graph UI components not initialized.")
			QMessageBox.critical(self, "Error", "Graph visualization is not properly initialized.")
			return

		try:
			# ✅ Clear existing plot
			self.ax.clear()

			# ✅ Extract values
			x_values = dataframe["Wavelength (nm)"].values
			y_values = dataframe["Absorbance"].values

			# ✅ Apply optional smoothing
			if hasattr(self, 'savgol_checkbox') and self.savgol_checkbox.isChecked():
				from scipy.signal import savgol_filter
				window_size = self.savgol_window_size.value()
				poly_order = self.savgol_polyorder.value()

				if window_size > len(y_values):
					logging.warning(f"⚠ Window size ({window_size}) too large. Reducing to valid range.")
					window_size = max(3, len(y_values) - 1)

				if window_size % 2 == 0:
					logging.warning(f"⚠ Window size ({window_size}) must be odd. Increasing by 1.")
					window_size += 1

				if poly_order >= window_size:
					logging.warning(f"⚠ Polynomial order ({poly_order}) too high. Adjusting.")
					poly_order = max(1, window_size - 1)

				y_values = savgol_filter(y_values, window_size, poly_order)

			# ✅ Apply Matplotlib styling (White background, Red line, Rounded corners)
			self.ax.set_facecolor("white")
			self.ax.plot(x_values, y_values, color="red", linewidth=2, label="Absorbance Spectrum")
			self.ax.set_xlabel("Wavelength (nm)")
			self.ax.set_ylabel("Absorbance")
			self.ax.set_title("Spectral Absorbance Visualization")
			self.ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
			self.ax.spines['top'].set_visible(False)
			self.ax.spines['right'].set_visible(False)

			# ✅ Apply rounded border to Matplotlib widget
			self.canvas.setStyleSheet("border-radius: 10px; background-color: white; padding: 5px;")

			# ✅ Update and refresh canvas
			self.canvas.draw()
			logging.info("✅ Graph updated successfully.")

		except Exception as e:
			logging.error(f"❌ Error updating graph: {str(e)}")
			QMessageBox.critical(self, "Visualization Error", f"Failed to update graph: {str(e)}")

	def update_table_view(self, dataframe):
		"""
		Updates the AI quantification table during Step 3 (quantification results).
		Formats AI deconvolution results into a structured 5-row, 5-column table with a rounded design.
		"""
		# ✅ Ensure this is only shown in Step 3
		if self.current_step != 3:
			logging.warning("⚠ Table update skipped: Not in quantification step.")
			return

		if dataframe is None or dataframe.empty:
			QMessageBox.warning(self, "No Data", "No spectral data available for analysis.")
			return

		# ✅ Ensure required columns exist
		required_columns = ["Wavelength (nm)", "Absorbance"]
		if not all(col in dataframe.columns for col in required_columns):
			logging.error("❌ Missing required columns for peak analysis.")
			QMessageBox.critical(self, "Error", "Peak analysis table must have 'Wavelength (nm)' and 'Absorbance'.")
			return

		try:
			from scipy.signal import find_peaks

			# ✅ Perform Peak Detection with AI Quantification Data
			peaks, properties = find_peaks(dataframe["Absorbance"], prominence=np.std(dataframe["Absorbance"]) * 0.5)

			nm_values = dataframe["Wavelength (nm)"].iloc[peaks].values
			intensity_values = dataframe["Absorbance"].iloc[peaks].values
			prominence_values = properties["prominences"]

			# ✅ Ensure AI Deconvolution Quantification Exists
			if not hasattr(self, "deconvolution_results") or not self.deconvolution_results:
				logging.error("❌ AI deconvolution results missing.")
				return

			# ✅ Extract AI Quantification Data
			ai_quantification = {
				"C complexes": self.deconvolution_results.get("C_complex_count", "N/A"),
				"CC complexes": self.deconvolution_results.get("CC_complex_count", "N/A"),
				"CCC complexes": self.deconvolution_results.get("CCC_complex_count", "N/A"),
				"Oxidized HRP (Soret Band)": self.deconvolution_results.get("Oxidized_HRP_count", "N/A")
			}

			# ✅ Format values into scientific notation
			formatted_quantities = {key: f"{value:.2E}" if isinstance(value, (int, float)) else value
									for key, value in ai_quantification.items()}

			# ✅ Prepare Data for Display
			analytes = list(formatted_quantities.keys())
			quantities = list(formatted_quantities.values())
			nm_values_str = ", ".join([f"{v:.2f}" for v in nm_values]) if nm_values.size else "N/A"
			intensity_values_str = ", ".join([f"{v:.2f}" for v in intensity_values]) if intensity_values.size else "N/A"
			prominence_values_str = ", ".join([f"{v:.2f}" for v in prominence_values]) if prominence_values.size else "N/A"

			# ✅ Create step3_layout if it doesn't exist
			if not hasattr(self, "step3_layout"):
				self.step3_layout = QVBoxLayout()
				self.quantification_screen = QWidget()
				self.quantification_screen.setLayout(self.step3_layout)
				self.main_layout.addWidget(self.quantification_screen)
				self.quantification_screen.setVisible(self.current_step == 3)

			# ✅ Ensure Table Exists
			if not hasattr(self, "analysis_table"):
				self.analysis_table = QTableWidget()
				self.analysis_table.setColumnCount(5)
				self.analysis_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
				self.analysis_table.setStyleSheet(
					"QTableWidget {"
					"    background: white;"
					"    border-radius: 15px;"
					"    padding: 5px;"
					"}"
					"QHeaderView::section {"
					"    background-color: #f0f0f0;"
					"    border-bottom: 2px solid gray;"
					"    font-weight: bold;"
					"}"
				)

				# ✅ Add a separator below the table (Gray Dotted Line, 4px Weight)
				self.table_separator = QFrame()
				self.table_separator.setFrameShape(QFrame.Shape.HLine)
				self.table_separator.setFrameShadow(QFrame.Shadow.Plain)
				self.table_separator.setStyleSheet("border: 4px dashed gray; margin-top: 10px; margin-bottom: 10px;")

				# ✅ Add widgets to step3_layout
				self.step3_layout.addWidget(self.analysis_table)
				self.step3_layout.addWidget(self.table_separator)

			# ✅ Corrected: Ensure column count matches the headers
			self.analysis_table.setColumnCount(5)

			# ✅ Title Row (Bold)
			title_headers = [
				"Analyte:", 
				"Quantity In 1 mL Assay Environment:", 
				"Wavelength(s) Relevant For AI Quantification", 
				"Intensity at Relevant Wavelength(s)", 
				"Prominence at Relevant Wavelength(s)"
			]

			for col, title in enumerate(title_headers):
				item = QTableWidgetItem(title)
				item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
				item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				self.analysis_table.setItem(0, col, item)

			# ✅ Populate Data Rows
			self.analysis_table.setRowCount(len(analytes) + 1)  # +1 for the title row
			for row, analyte in enumerate(analytes, start=1):
				self.analysis_table.setItem(row, 0, QTableWidgetItem(analyte))  # Analyte Name
				self.analysis_table.setItem(row, 1, QTableWidgetItem(quantities[row-1]))  # Quantity
				self.analysis_table.setItem(row, 2, QTableWidgetItem(nm_values_str))  # nm Values
				self.analysis_table.setItem(row, 3, QTableWidgetItem(intensity_values_str))  # Intensity
				self.analysis_table.setItem(row, 4, QTableWidgetItem(prominence_values_str))  # Prominence

			# ✅ Center Align & Expandable Layout (Like Google Docs Chart)
			for col in range(5):
				self.analysis_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
				self.analysis_table.horizontalHeaderItem(col).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

			logging.info("✅ AI Quantification Table updated successfully.")

		except Exception as e:
			logging.error(f"❌ Error updating AI quantification table: {str(e)}")
			QMessageBox.critical(self, "Error", f"Failed to update AI quantification table: {str(e)}")
			
	def bayesian_savgol_optimization(self):
		"""
		Uses Bayesian Optimization to find optimal Savitzky-Golay parameters dynamically.
		- Prevents UI freezing using `QApplication.processEvents()`.
		- Includes a loading spinner like `ai_savgol_recommendation()`.
		- Ensures per-segment parameter optimization.
		- Uses Bayesian inference to select the best parameters.
		"""
		try:
			# ✅ Ensure we're in the correct step
			if self.current_step != 1:
				logging.warning("⚠ Bayesian Optimization skipped: Not in preprocessing step.")
				return
			
			# ✅ Ensure Savitzky-Golay filter is enabled
			if not hasattr(self, 'savgol_checkbox') or not self.savgol_checkbox.isChecked():
				QMessageBox.warning(self, "Bayesian Optimization Skipped", "Enable Savitzky-Golay filter before optimization.")
				return

			# ✅ Prevent multiple executions at the same time
			if hasattr(self, 'is_bayesian_running') and self.is_bayesian_running:
				logging.warning("⚠ Bayesian Optimization already running. Skipping redundant execution.")
				return

			self.is_bayesian_running = True  # ✅ Prevent duplicate execution

			# ✅ Show loading spinner with parent check to avoid Qt errors
			if not hasattr(self, 'loading_label'):
				self.loading_label = QLabel(self)
				self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
				self.loading_label.setStyleSheet("background: rgba(0, 0, 0, 0.7); border-radius: 15px; padding: 10px;")
				self.loading_label.setGeometry(400, 200, 400, 400)

			if self.loading_label.parent() is not None:
				self.loading_label.setParent(None)
			self.layout().addWidget(self.loading_label)  # Add safely after reparenting

			# ✅ Loading spinner setup (avoid duplication)
			spinner_path = "assets/loading_spinner_white.gif"
			if not hasattr(self, 'loading_spinner'):
				self.loading_spinner = QMovie(spinner_path)
				self.loading_label.setMovie(self.loading_spinner)
			elif self.loading_label.movie() is None:
				self.loading_label.setMovie(self.loading_spinner)

			self.loading_spinner.start()
			self.loading_label.setVisible(True)

			QApplication.processEvents()  # ✅ Prevent UI freeze

			# ✅ Ensure data exists and is numeric
			if not hasattr(self, 'data') or self.data is None or self.data.empty:
				QMessageBox.warning(self, "No Data", "No data available for Bayesian Optimization.")
				self.is_bayesian_running = False
				self.loading_label.setVisible(False)
				return

			try:
				x_values = self.data["Wavelength (nm)"].astype(float).values
				y_values = self.data["Absorbance"].astype(float).values
			except ValueError:
				QMessageBox.critical(self, "Data Error", "Non-numeric values detected in dataset. Ensure valid CSV format.")
				self.is_bayesian_running = False
				self.loading_label.setVisible(False)
				return

			N = len(y_values)
			if N < 10:
				QMessageBox.warning(self, "Insufficient Data", "Too few data points for optimization.")
				self.is_bayesian_running = False
				self.loading_label.setVisible(False)
				return

			# ✅ Define objective function for Bayesian Optimization
			def objective(params):
				"""Objective function to minimize noise in the first derivative."""
				window_size, poly_order = params
				window_size = max(5, min(31, window_size))
				if window_size % 2 == 0:
					window_size += 1  # ✅ Ensure odd window size
				poly_order = max(2, min(poly_order, window_size - 1))

				smoothed = savgol_filter(y_values, window_size, poly_order)
				return np.std(np.gradient(smoothed))  # ✅ Minimizing change in first derivative (avoiding over-smoothing)

			# ✅ Bayesian Optimization search
			space = [Integer(5, 31), Integer(2, 4)]
			self.loading_label.setText("🔄 Running Bayesian Optimization...")
			QApplication.processEvents()  # ✅ Prevent UI freeze

			result = gp_minimize(objective, space, n_calls=15, random_state=42)

			# ✅ Retrieve optimized values
			best_window, best_poly = result.x
			if best_window % 2 == 0:
				best_window += 1  # ✅ Ensure odd window size

			# ✅ Apply values to UI
			self.savgol_window_size.setValue(best_window)
			self.savgol_polyorder.setValue(best_poly)

			# ✅ Apply optimized smoothing and update graph
			self.update_graph_view(self.data)

			self.loading_label.setText("✅ Bayesian Optimization Complete!")
			QApplication.processEvents()  # ✅ Ensure final UI update

			# ✅ Show confirmation message
			QMessageBox.information(self, "Bayesian Optimization Applied", 
									f"✅ Optimized Savitzky-Golay Parameters Applied:\n"
									f"🔹 Window Length: {best_window}\n"
									f"🔹 Polynomial Order: {best_poly}")

			logging.info(f"✅ Bayesian Optimization applied successfully with Window: {best_window}, Polyorder: {best_poly}")

		except Exception as e:
			logging.error(f"❌ Error in Bayesian Optimization: {e}")
			QMessageBox.critical(self, "Error", f"⚠ An error occurred: {e}")

		finally:
			self.is_bayesian_running = False  # ✅ Allow next execution
			self.loading_label.setVisible(False)  # ✅ Hide spinner after completion

if __name__ == "__main__":
	import sys
	import logging
	import traceback
	from PyQt6.QtWidgets import QApplication
	from PyQt6.QtCore import Qt

	# ✅ Configure Logging with Line Numbers
	LOG_FILE = "cono_bot.log"
	logging.basicConfig(
		filename=LOG_FILE,
		level=logging.ERROR,
		format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
	)
	# ✅ Global Exception Handler to Catch Uncaught Errors
	def handle_exception(exc_type, exc_value, exc_traceback):
		"""Handles uncaught exceptions, logs them with line numbers."""
		if issubclass(exc_type, KeyboardInterrupt):
			sys.__excepthook__(exc_type, exc_value, exc_traceback)
			return
		error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
		logging.error("🔥 Uncaught Exception:\n" + error_message)
		print(f"🚨 Error occurred! Check {LOG_FILE} for details.")

	sys.excepthook = handle_exception  # ✅ Apply the global exception handler

	# ✅ Prevent multiple QApplication instances
	app = QApplication.instance()
	if app is None:
		app = QApplication(sys.argv)

	# ✅ KDE/Wayland compatibility settings
	app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

	# ✅ Set KDE application metadata
	app.setApplicationName("ConoBot")
	app.setApplicationDisplayName("ConoBot")
	app.setOrganizationName("ConoBot Project")
	app.setOrganizationDomain("conobot.org")

	try:
		# ✅ Initialize ConoBot (which contains all sub-functions)
		window = ConoBot()
		window.show()

		# ✅ Start the PyQt event loop
		sys.exit(app.exec())

	except Exception:
		logging.error("❌ Fatal error during application startup:", exc_info=True)
		sys.exit(1)  # ✅ Ensure clean exit on crash