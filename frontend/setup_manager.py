# Standard Library Imports
import sys
import os
import logging
import time
import datetime
import shutil

#Imports from PyQt6
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QLabel, QPushButton, QApplication
)
from PyQt6.QtGui import QFont, QIcon

class SetupManager(QMainWindow):
	
	@staticmethod
	def run_initial_setup(parent):
		
		# Use QMainWindow for the setup window 
		setup_window = QMainWindow(parent)
		setup_window.setWindowTitle("Welcome to ConoBot - Setup")
		setup_window.setGeometry(100, 100, 600, 350)  # This sets initial size, but window remains resizable
		setup_window.setMinimumSize(600, 350)  # Set minimum size to prevent shrinking

		bg_image_path = "/usr/share/conobot/assets/setup_screen_background.png"
		if not os.path.exists(bg_image_path):
			logging.error(f"Background image not found at {bg_image_path}.")
			return

		# Set background using a central widget and stylesheet
		central_widget = QWidget()
		setup_window.setCentralWidget(central_widget)
		central_widget.setStyleSheet(
			f"QWidget {{"
			f"background-image: url('{bg_image_path}');"
			"background-repeat: no-repeat;"
			"background-position: center;"
			"background-size: cover;"
			"}}"
		)

		setup_layout = QVBoxLayout(central_widget)  # Layout for *this* window only

		panel_container = QWidget()
		panel_container.setStyleSheet(
			"background-size: cover;"
			"border-radius: 15px;"
			"padding: 15px;"
			"background-color: rgba(255, 255, 255, 0.8);"  # Semi-transparent white
			"border: 2px solid black;"
		)

		panel_layout = QVBoxLayout(panel_container)  # Layout for the panel

		welcome_label = QLabel("Welcome to ConoBot!")
		welcome_label.setFont(QFont("Verdana", 20, QFont.Weight.Bold))
		welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		welcome_label.setStyleSheet("color: black; margin-bottom: 10px;")

		description_label = QLabel("ConoBot AI - Advanced Conversational AI Assistant\nfor Amide Mapping and Spectra-based De Novo Analysis")
		description_label.setFont(QFont("Verdana", 12, QFont.Weight.Normal))
		description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		description_label.setStyleSheet("color: black; margin-bottom: 20px;")

		setup_info_label = QLabel("Setting up ConoBot for local AI processing...")
		setup_info_label.setFont(QFont("Verdana", 14, QFont.Weight.Normal))
		setup_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		setup_info_label.setStyleSheet("color: #2c3e50; margin-bottom: 15px;")

		continue_button = QPushButton("Continue to ConoBot")
		continue_button.setStyleSheet(
			"border-radius: 8px;"
			"background-color: #3498db;"
			"color: white;"
			"padding: 12px 24px;"
			"font-size: 14px;"
			"font-weight: bold;"
		)
		continue_button.clicked.connect(lambda: SetupManager.complete_setup(setup_window))

		# Add widgets to panel_layout
		panel_layout.addWidget(welcome_label)
		panel_layout.addWidget(description_label)
		panel_layout.addWidget(setup_info_label)
		panel_layout.addWidget(continue_button, alignment=Qt.AlignmentFlag.AlignCenter)

		# Add panel_container to setup_layout
		setup_layout.addWidget(panel_container, alignment=Qt.AlignmentFlag.AlignCenter)

		# Show the QMainWindow as a modal window
		setup_window.setWindowModality(Qt.WindowModality.ApplicationModal)
		setup_window.show()

	@staticmethod
	def complete_setup(setup_window):
		"""Complete the setup process and close the setup window."""
		setup_window.close()
		
