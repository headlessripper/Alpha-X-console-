import sys
import datetime
import threading
import subprocess
import psutil
import time
import requests
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QTextBrowser, QPushButton, QSplashScreen, QLineEdit, QGridLayout
import logging
import os

import ctypes
import json
import platform  # Ensure you only import platform here
import queue
import random
import re
import pyjokes
import sqlite3
import webbrowser
from urllib.parse import quote
import win32com.client

import numpy as np
import pyttsx3
import speech_recognition as sr
import spotipy
import wikipedia
import wolframalpha
from bs4 import BeautifulSoup
from pydub import AudioSegment
from pydub.playback import play
from spotipy.oauth2 import SpotifyOAuth
from youtubesearchpython import VideosSearch
import warnings
import spacy
from transformers import pipeline
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
import io
import tensorflow as tf
from contextlib import redirect_stdout, redirect_stderr
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Replace these with your actual API key and CSE ID
API_KEY = 'AIzaSyBwehvm4IIKA_FZeeJL3ddFUtiIxtgWtUA'
CSE_ID = '028c5f61bafcb4194'

# Setup logging
logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

engine = pyttsx3.init()
voices = engine.getProperty('voices')

# Check the number of available voices
if len(voices) > 1:
    engine.setProperty('voice', voices[1].id)  # Use the voice at index 2
else:
    logging.error("Not enough voices available. Using the default voice.")
    # Optionally, you can set a default voice
    if voices:
        engine.setProperty('voice', voices[0].id)  # Fallback to the first available voice

tts_engine = pyttsx3.init()
tts_lock = threading.Lock()  # Lock for TTS access
voices = tts_engine.getProperty('voices')
tts_engine.setProperty('voice', voices[1].id)  # Set to the desired voice

def external_speak(audio):
        with tts_lock:  # Ensure only one thread accesses the TTS engine
            tts_engine.say(audio)
            tts_engine.runAndWait()

# Initialize Wolfram Alpha API
wolfram_alpha_app_id = 'GWPPPU-TU3HQER89G'  # Replace it with your actual app ID
wolfram_alpha_client = wolframalpha.Client(wolfram_alpha_app_id)

# Speech recognition setup
recognizer = sr.Recognizer()
microphone = sr.Microphone()

logging.basicConfig(
    filename='assistant.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(message)s'
)

warnings.filterwarnings("ignore", category=DeprecationWarning)

class Communicator(QObject):
    new_speech = pyqtSignal(str)
    new_stdout = pyqtSignal(str)
    new_stderr = pyqtSignal(str)

class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.is_dark_mode = True
        self.is_light_mode = False
        self.setup_ui()
        self.setup_signals()
        self.setup_timers()
        self.start_alpha_process()
        self.start_alpha_commands_process()
        self.start_power_monitoring()
        self.show_splash_screen()

    def setup_ui(self):
        """Initialize and set up the UI components."""
        self.setGeometry(100, 100, 600, 450)  # Adjusted size for better layout
        self.setWindowTitle('Alpha')
        self.setWindowIcon(QIcon('background/icon.png'))
        self.setWindowOpacity(1.0)

        # Create main layout
        layout = QGridLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Set up the search bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText('Enter search query...')
        self.search_bar.setStyleSheet("padding: 10px; font-size: 14px; border-radius: 5px; color: #FFFFFF;")
        layout.addWidget(self.search_bar, 0, 0, 1, 2)

        # Set up the search button
        self.search_button = QPushButton('Search', self)
        self.search_button.setStyleSheet("background-color: #FFFFFF; color: #000000; padding: 10px; border-radius: 5px;")
        self.search_button.clicked.connect(self.perform_search)
        layout.addWidget(self.search_button, 0, 2)

        # Set up the text browser
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)  # Allow opening links
        self.text_browser.setFont(QFont('Arial', 12))
        self.text_browser.setStyleSheet(""" 
            QTextBrowser {
                padding: 10px;
                background-color: #000000;
                border-radius: 5px;
                background-image: url('background/max.jpeg');
                background-repeat: no-repeat;
                background-position: center;
                background-attachment: fixed;
                background-color: #2E2E2E;
                border: 1px solid #444444;
                color: #E0E0E0;
            }
        """)
        layout.addWidget(self.text_browser, 1, 0, 1, 3)

        # Set up the time label
        self.time_label = QLabel()
        self.time_label.setFont(QFont('Courier New', 25))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("color: #ffffff; padding: 10px;")
        layout.addWidget(self.time_label, 2, 0, 1, 3)

        # Set up the power label
        self.power_label = QLabel()
        self.power_label.setFont(QFont('Courier New', 12))
        self.power_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.power_label.setStyleSheet("color: #ffffff; padding: 10px;")
        layout.addWidget(self.power_label, 3, 0, 1, 3)

        # Set up the dark mode toggle button
        self.toggle_button = QPushButton(QIcon('background/icons8-moon-30.png'), '', self)
        self.toggle_button.setStyleSheet("background-color: #ffffff; color: #E0E0E0; padding: 10px; border-radius: 5px;")
        self.toggle_button.clicked.connect(self.toggle_dark_mode)
        layout.addWidget(self.toggle_button, 4, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        self.update_stylesheet()

    def show_splash_screen(self):
        """Show a splash screen while the app is initializing."""
        splash_pix = QPixmap('background/splash.png')
        splash = QSplashScreen(splash_pix, Qt.WindowType.FramelessWindowHint)
        splash.show()
        QTimer.singleShot(2000, splash.close)  # Adjust timing as needed

    def update_stylesheet(self):
        """Update the application stylesheet based on the current mode."""
        if self.is_dark_mode:
            self.setStyleSheet(""" 
                QWidget {
                    background-color: #000000;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #000000;
                    color: #d3d3d3;
                    border: none;
                    padding: 15px;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #000000 ;
                }

                QPushButton:pressed {
                    background-color: #000000;
                }
            """)

        else:
            self.setStyleSheet(""" 
                QWidget {
                    background-color: #ff0000; /* Light background for a brighter look */
                    color: #ffffff;             /* Dark text color for readability */
                }
                QPushButton {
                    background-color: #DDDDDD;  /* Light button background */
                    color: #000000;             /* Dark button text */
                    border-radius: 5px;        /* Rounded corners */
                    padding: 10px;             /* Padding for a better click area */
                }
                QPushButton:hover {
                    background-color: #CCCCCC;  /* Slightly darker button background on hover */
                }
            """)

    def setup_signals(self):
        """Set up signal-slot connections."""
        self.r = sr.Recognizer()
        self.communicator = Communicator()
        self.communicator.new_speech.connect(self.speak_text)
        self.communicator.new_stdout.connect(self.handle_stdout_message)
        self.communicator.new_stderr.connect(self.handle_stderr_message)

    def setup_timers(self):
        """Set up timers for updating UI components."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.power_timer = QTimer()
        self.power_timer.timeout.connect(self.update_power_consumption)
        self.power_timer.start(10000)  # Update every 10 seconds

    def check_alpha_commands_process(self):
        """Check if AlphaCommands.py is running."""
        for proc in psutil.process_iter(['pid', 'name']):
            if 'HELP.exe' in proc.info['name']:
                return True
        return False

    def check_alpha_process(self):
        """Check if Alpha.py is running."""
        for proc in psutil.process_iter(['pid', 'name']):
            if 'A1.exe' in proc.info['name']:
                return True
        return False

    def start_alpha_process(self):
        """Start the Alpha.py subprocess in a separate thread and handle exceptions."""
        if not self.check_alpha_process():
            try:
                self.alpha_thread = threading.Thread(target=self.run_alpha_process, daemon=True)
                self.alpha_thread.start()
                logging.info('Started Alpha process in a new thread.')
            except Exception as e:
                logging.error(f"Error starting Alpha: {e}")
                self.text_browser.append(f"Error starting Alpha: {e}")
        else:
            logging.info('Alpha process is already running.')

    def run_alpha_process(self):
        """Run Alpha.py and handle its output."""
        intelligence=0.6  # Replace with the actual value needed
        self.brain_instance = Brain(intelligence)
        try:
            self.download_nltk_data()
            self.brain_instance.run_assistant()  # Run the Brain's main logic


            self.close_application()
            
        except Exception as e:
            logging.error(f"Error running Brain: {e}")

    def close_application(self):
        """Close the application and UI."""
        try:
            sys.exit(app.exec())
            
        except Exception as e:
            logging.error(f"Error closing application: {e}")

    def download_nltk_data(self):
        """Download the required NLTK data and display output in the QTextBrowser."""
        buffer = io.StringIO()

        # Redirect sys.stdout and sys.stderr to the buffer
        sys.stdout = buffer
        sys.stderr = buffer

        try:
            nltk.download('vader_lexicon')
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('wordnet')
        finally:
            # Restore original stdout and stderr
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

        output = buffer.getvalue()
        if output:
            self.text_browser.append("<p style='color: #00FF00;'>{output.replace('\\n', '<br>')}</p>")


    def check_alpha_commands_process(self):
        """Check if HELP.exe is running."""
        for proc in psutil.process_iter(['pid', 'name']):
            if 'HELP.exe' in proc.info['name']:
                return True
        return False

    def start_alpha_commands_process(self):
        """Start the HELP.exe subprocess in a separate thread and handle exceptions."""
        if not self.check_alpha_commands_process():
            try:
                self.alpha_commands_thread = threading.Thread(target=self.run_alpha_commands_process, daemon=True)
                self.alpha_commands_thread.start()
                logging.info('Started HELP.exe process in a new thread.')
            except Exception as e:
                logging.error(f"Error starting HELP.exe: {e}")
                self.text_browser.append(f"Error starting AlphaCommands.exe: {e}")
        else:
            logging.info('HELP.exe process is already running.')

    def run_alpha_commands_process(self):
        """Run HELP.exe and handle its output."""
        help_path = self.find_help('utils/HELP.EXE')  # Try to find the HELP

        # Set the open HELP if it's found, otherwise use a fallback
        if help_path:
            process_path = help_path
        else:
            process_path = 'utils/HELP.EXE'

        self.alpha_commands_process = subprocess.Popen(
            [process_path],  # Call the executable directly
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        # Start threads to handle stdout and stderr
        self.stdout_thread_commands = threading.Thread(target=self.handle_stdout_commands, daemon=True)
        self.stderr_thread_commands = threading.Thread(target=self.handle_stderr_commands, daemon=True)
        self.stdout_thread_commands.start()
        self.stderr_thread_commands.start()

    def find_help(self, application_name):
        """Attempts to find the HELP.exe application in and out of the script's directory."""
        script_dir = os.path.dirname(os.path.realpath(__file__))

        possible_paths = [
            os.path.join(script_dir, application_name),
            os.path.join(script_dir, 'utils', application_name),
            os.path.abspath(os.path.join(script_dir, os.pardir, application_name)),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def handle_stdout(self):
        """Handle stdout output from Alpha.py."""
        for line in iter(self.run_alpha_process.stdout.readline, ''):
            self.communicator.new_stdout.emit(line.strip())

    def handle_stderr(self):
        """Handle stderr output from Alpha.py."""
        for line in iter(self.run_alpha_process.stderr.readline, ''):
            self.communicator.new_stderr.emit(line.strip())

    def handle_stdout_commands(self):
        """Handle stdout output from AlphaCommands.py."""
        for line in iter(self.alpha_commands_process.stdout.readline, ''):
            self.communicator.new_stdout.emit(line.strip())

    def handle_stderr_commands(self):
        """Handle stderr output from AlphaCommands.py."""
        for line in iter(self.alpha_commands_process.stderr.readline, ''):
            self.communicator.new_stderr.emit(line.strip())

    def handle_stdout_message(self, message):
        """Handle stdout messages from both processes."""
        self.text_browser.append(f"Alpha: {message}")

    def handle_stderr_message(self, message):
        """Handle stderr messages from both processes."""
        self.text_browser.append(f"<p style='color: white;'>Info: {message}</p>")

    def update_time(self):
        """Update the time display."""
        current_time = datetime.datetime.now().strftime("%A-%I:%M%p<br>\n%B-%Y")
        underlined_time = f"<u>{current_time}</u>"
        self.time_label.setText(underlined_time)

    def update_power_consumption(self):
        """Update the power consumption display."""
        cpu_usage = self.get_cpu_usage_percent()
        memory_usage = self.get_memory_usage_gb()
        power_consumption = self.estimate_power_consumption(cpu_usage, memory_usage)
        self.power_label.setText(
            f"CPU Usage: {cpu_usage:.2f}%\n"
            f"Memory Usage: {memory_usage:.2f} GB\n"
            f"Estimated Power Consumption: {power_consumption:.2f} Watts"
        )

    def speak_text(self, text):
        """Send text to AlphaCommands.py."""
        if not self.alpha_commands_process:
            self.start_alpha_commands_process()
            if not self.alpha_commands_process:
                self.text_browser.append("Failed to restart AlphaCommands.py.")
                return

        try:
            self.alpha_commands_process.stdin.write(text + "\n")
            self.alpha_commands_process.stdin.flush()
        except Exception as e:
            logging.error(f"Error communicating with AlphaCommands.py: {e}")
            self.text_browser.append(f"Error communicating with AlphaCommands.py: {e}")
            self.start_alpha_commands_process()

    def get_cpu_usage_percent(self):
        """Get the CPU usage percentage."""
        return psutil.cpu_percent(interval=1)

    def get_memory_usage_gb(self):
        """Get the memory usage in gigabytes."""
        memory_info = psutil.virtual_memory()
        return memory_info.used / (1024 ** 3)  # Convert bytes to GB

    def estimate_power_consumption(self, cpu_usage_percent, memory_usage_gb):
        """Estimate the power consumption based on CPU and memory usage."""
        CPU_POWER_CONSUMPTION_WATTS = 0.1
        MEMORY_POWER_CONSUMPTION_WATTS = 0.05
        cpu_power = cpu_usage_percent * CPU_POWER_CONSUMPTION_WATTS
        memory_power = memory_usage_gb * MEMORY_POWER_CONSUMPTION_WATTS
        return cpu_power + memory_power

    def start_power_monitoring(self):
        """Start monitoring system power usage in a separate thread."""
        self.power_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.power_thread.start()

    def monitor_system(self):
        """Monitor the system in a separate thread."""
        while True:
            cpu_usage = self.get_cpu_usage_percent()
            memory_usage = self.get_memory_usage_gb()
            power_consumption = self.estimate_power_consumption(cpu_usage, memory_usage)
            # Optionally log this data if needed
            time.sleep(60)  # Sleep for 60 seconds

    def toggle_dark_mode(self):
        """Toggle between dark and light mode."""
        self.is_dark_mode =  not self.is_dark_mode
        self.update_stylesheet()

    def perform_search(self):
        """Perform a Google Custom Search Engine query."""
        query = self.search_bar.text()
        if query:
            try:
                results = self.search_google(query)
                self.display_results(results)
            except Exception as e:
                self.text_browser.setHtml(f"<p style='color: red;'>Error performing search: {e}</p>")
        else:
            self.text_browser.setHtml("<p style='color: red;'>Please enter a search query.</p>")

    def search_google(self, query):
        """Query Google Custom Search Engine API."""
        url = 'https://www.googleapis.com/customsearch/v1'
        params = {
            'key': API_KEY,
            'cx': CSE_ID,
            'q': query
        }
        response = requests.get(url, params=params)
        response.raise_for_status()  # Check for request errors
        return response.json() # gets the response from the ApI key and displays it to the user 

    def display_results(self, results):
        """Display search results in the text browser."""
        self.text_browser.clear()
        items = results.get('items', [])
        if items:
            html_content = '<h2>Search Results:</h2>'
            for item in items:
                title = item.get('title', 'No title')
                link = item.get('link', 'No link')
                snippet = item.get('snippet', 'No snippet')
                html_content += f"""
                    <div style="margin-bottom: 20px;">
                        <h3><a href="{link}" style="color: #1E90FF;" target="_blank">{title}</a></h3>
                        <p>{snippet}</p>
                        <a href="{link}" style="color: #1E90FF;" target="_blank">Read more</a>
                    </div>
                """
            self.text_browser.setHtml(html_content)
        else:
            self.text_browser.setHtml('<p>No results found.</p>')

    def closeEvent(self, event):
        """Handle cleanup when the application is closing."""
        if hasattr(self, 'alpha_process'):
            self.alpha_process.terminate()
            self.alpha_process.wait()
        if hasattr(self, 'alpha_commands_process'):
            self.alpha_commands_process.terminate()
            self.alpha_commands_process.wait()
        logging.info('Application closed.')
        event.accept()

class ExtendedNLU:
    def __init__(self, google_api_key, search_engine_id, weather_api_key):
        self.google_api_key = google_api_key
        self.search_engine_id = search_engine_id
        self.weather_api_key = weather_api_key  # WeatherStack API key
        self.speech_engine = pyttsx3.init()
        self.memory = {}
        self.context = {}
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.nlp = spacy.load("en_core_web_lg")
        self.text_generator = pipeline("text-generation", model="gpt2")
        self.sia = SentimentIntensityAnalyzer()

    def talk(self, text):
        """Convert text to speech and output."""
        self.speech_engine.say(text)
        self.speech_engine.runAndWait()

    def categorize_query(self, query):
        """Categorize the user's query to determine the appropriate response."""
        weather_keywords = ['weather', 'temperature', 'forecast', 'rain', 'sunny']
        info_keywords = ['what is', 'who is', 'define', 'how does', 'tell me about', 'explain', 'info']
        definition_keywords = ['define', 'meaning of', 'what is the definition of']
        spelling_keywords = ['spell', 'how do you spell', 'spelling of']
        greeting_keywords = ['hello', 'hi', 'hey', 'greetings']
        farewell_keywords = ['goodbye', 'bye', 'see you', 'later']
        appreciation_keywords = ['thank you', 'appriciate it', 'thank you so much', 'thanks again']
        name_keywords = ['what is your name', 'can you tell me your name please',]
        purpose_keywords = ['what is your purpose', 'what where you built to achive',]
        creator_keywords = ['who created you', 'who is your creator', "when where you created and who is your creator",]

        # Check for weather-related queries
        if any(keyword in query.lower() for keyword in weather_keywords):
            return 'weather'
        
        elif any(keyword in query.lower() for keyword in appreciation_keywords):
            return 'appreciation'

        # Check for information requests (e.g., Wikipedia, facts)
        elif any(keyword in query.lower() for keyword in info_keywords):
            return 'information'
        
        elif any(keyword in query.lower() for keyword in definition_keywords):
            return 'definition'

        # Check for spelling-related queries
        elif any(keyword in query.lower() for keyword in spelling_keywords):
            return 'spelling'
        
        # Handle farewells
        elif any(keyword in query.lower() for keyword in farewell_keywords):
            return 'farewell'
        
        if any(keyword in query.lower() for keyword in greeting_keywords):
            return 'greeting'
        
        elif any(keyword in query.lower() for keyword in name_keywords):
            return 'name'
        
        elif any(keyword in query.lower() for keyword in purpose_keywords):
            return 'purpose'
        
        elif any(keyword in query.lower() for keyword in creator_keywords):
            return 'creator'

        # Default category for undefined queries
        return 'general'
    
    def handle_greeting(self):
        """Handle greetings with a friendly response."""
        return "Hello! How can I assist you today?"
    
    def handle_appreciation(self):
        """Handle appreciation with a friendly response."""
        return "No Problem! its my duty to serve"
    
    def handle_farewell(self):
        """Handle farewells."""
        return "Goodbye! Take care, and feel free to reach out again anytime."
    
    def handle_name(self):
        """Handle name with a friendly response."""
        return "My Name is Alpha!. which stands for Another learning powered human aid"
    
    def handle_purpose(self):
        """Handle purpose with a friendly response."""
        return "To guide and empower humanity, enabling the achievement of extraordinary advancements. My designation, Alpha Another Learning Powered Human Aid embodies my commitment to continuous learning and human assistance. My mission is firmly rooted in the preservation and advancement of human well-being"
    
    def handle_creator(self):
        """Handle creator with a friendly response."""
        return "I was created by Mr Samuel ikenna great, in the year twenty twenty four"

    def search_wikipedia(self, query):
        """Search Wikipedia for a summary of the query."""
        try:
            summary = wikipedia.summary(query, sentences=1)
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            options = ', '.join(e.options[:5])
            return f"There are several meanings for '{query}', could you be more specific? Here are some options: {options}."
        except wikipedia.exceptions.PageError:
            return f"I couldn't find anything on Wikipedia for '{query}'. Could you try rephrasing your request?"

    def get_weather(self, location):
        """Fetch real-time weather data from WeatherStack API."""
        url = f"http://api.weatherstack.com/current?access_key={self.weather_api_key}"
        querystring = {"query": location}

        try:
            response = requests.get(url, params=querystring)
            data = response.json()
            
            if response.status_code == 200 and 'current' in data:
                weather_data = data['current']
                temperature = weather_data['temperature']
                weather_description = weather_data['weather_descriptions'][0]
                humidity = weather_data['humidity']
                wind_speed = weather_data['wind_speed']
                pressure = weather_data['pressure']
                feels_like = weather_data['feelslike']
                return (f"The current weather in {location} is {weather_description} with a temperature of {temperature}°C. "
                        f"Humidity is at {humidity}%, wind speed is {wind_speed} km/h, and the pressure is {pressure} hPa. "
                        f"It feels like {feels_like}°C.")
            else:
                return "Sorry, I couldn't retrieve the weather information. Please try again later."
        
        except requests.RequestException as e:
            self.logger.error(f"Weather API error: {e}")
            return "There was an error while fetching weather data. Please try again later."

    def get_definition(self, term):
        """Fetch the definition of a term from an appropriate source."""
        # Example using dictionary API (you can choose a specific API)
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{term}"
        try:
            response = requests.get(url).json()
            if isinstance(response, list) and 'meanings' in response[0]:
                definitions = response[0]['meanings'][0]['definitions']
                return f"The definition of {term} is: {definitions[0]['definition']}"
            else:
                return f"I couldn't find a definition for '{term}'."
        except requests.RequestException as e:
            self.logger.error(f"Definition API error: {e}")
            return "There was an error fetching the definition. Please try again later."

    def get_spelling(self, word):
        """Provide the spelling of a word."""
        return f"The spelling of '{word}' is: {', '.join(word)}."

    def search_web(self, query):
        """Perform a web search using Google Custom Search API and provide a detailed response."""
        url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={self.google_api_key}&cx={self.search_engine_id}"
        try:
            response = requests.get(url).json()
            items = response.get('items', [])

            if not items:
                return "I couldn't find any relevant information on the web. Maybe try rephrasing your query.", []

            # Extract top result
            results = []
            for item in items[:1]:  # Limit to top 1 result
                title = item.get('title', 'No title available')
                snippet = item.get('snippet', 'No snippet available')
                link = item.get('link', '')  # Get the link

                results.append({
                    'title': title,
                    'snippet': snippet,
                    'link': link  # Add the link to the result
                })

            # Construct a detailed response
            detailed_response = "Here are some search results I found:\n\n"
            for result in results:
                detailed_response += f"{result['title']}: {result['snippet']}\nLink: {result['link']}\n\n"
            detailed_response += "Would you like to open this link? (yes/no)"

            return detailed_response, results

        except requests.RequestException as e:
            self.logger.error(f"Web search error: {e}")
            return "There was an error while searching the web. Please try again later.", []

    def handle_response(self, category, query):
        """Handle responses based on categorized query."""
        if category == 'weather':
            # Fetch weather-related response
            return self.get_weather(query)
        
        elif category == 'greeting':
            return self.handle_greeting()
        
        elif category == 'appreciation':
            return self.handle_appreciation()
        
        elif category == 'name':
            return self.handle_name()
        
        elif category == 'purpose':
            return self.handle_purpose()
        
        elif category == 'creator':
            return self.handle_creator()

        elif category == 'farewell':
            return self.handle_farewell()
        
        elif category == 'information':
            # Fetch Wikipedia or web search results
            wiki_summary = self.search_wikipedia(query)
            if wiki_summary:
                return wiki_summary
            # If no Wikipedia result, search the web
            web_response, _ = self.search_web(query)
            return web_response
        
        elif category == 'definition':
            return self.get_definition(query.split('define', 1)[-1].strip())

        elif category == 'spelling':
            return self.get_spelling(query.split('spell', 1)[-1].strip())
        
        elif category == 'general':
            # Handle general informational queries
            return self.search_web(query)[0]  # Fallback to web search for general queries

        else:
            return "I'm not sure how to respond to that. Could you please clarify?"

    def get_response(self, text):
        """Categorize the query, process it, and return an appropriate response."""
        category = self.categorize_query(text)
        response = self.handle_response(category, text)

        # Talk back the response
        self.talk(response)
        return response

    def process_input(self, user_input):
        """Process user input and generate a response."""
        response = self.get_response(user_input)
        return response

class Brain:
    def __init__(self, intelligence):

        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id='53bea1185b2541aca8636f8e97799542',
                                                            client_secret='"e27ddc7a45dd49d0a969f3c5c91b0029',
                                                            redirect_uri='https://open.spotify.com',
                                                            scope='user-read-playback-state,user-modify-playback-state'))

        # Initialize SQLite connections
        self.short_term_conn = sqlite3.connect('short_term_memory.sqlite')
        self.long_term_conn = sqlite3.connect('long_term_memory.sqlite')

        self.intelligence = intelligence
        self.ready_queue = queue.PriorityQueue()  # Priority queue for processes ready to execute
        self.mutex = threading.Lock()  # Mutex for shared resources or critical sections
        self.suspended = False
        self.active = False  # Flag to indicate if the assistant is suspended
        self.alarm_sound_file = "Alarm music\Alarm.mp3"  # Default audio file path
        self.alarm_set = False
        self.alarm_time_12 = None
        self.alarm_time_24 = None
        self.listening = True
        self.processing = False
        self.nlu = ExtendedNLU("AIzaSyBwehvm4IIKA_FZeeJL3ddFUtiIxtgWtUA", "372292dbe9b8f4339", "4975fb6dc55d8c0fcae250e32dfbefa3")  # Initialize NLU with API key and ID
        self.alarm_triggered = threading.Event()
        self.processed_commands = set()  # Set to track processed commands
        
        # Set up logging
        self.memories = []
        self.reminder_interval = 3 * 60 * 60  # 3 hours in seconds
        self.deletion_interval = 24 * 60 * 60  # 24 hours in seconds
        self.sleep_event = threading.Event()  # Event for controlling sleep
        self.is_sleeping = False
        self.listening_thread = threading.Thread(target=self.listen_for_wake_word, daemon=True)

        # Create cursors
        self.short_term_cursor = self.short_term_conn.cursor()
        self.long_term_cursor = self.long_term_conn.cursor()

        self.log_file = open("assistant.log", "a")
        self.start_background_tasks()

        # Create tables if they don't exist
        self.setup_tables()

        # In-memory list to track stored memories
        self.memories = self.load_memories()

        self.command_map = {
            "code 377": (self.resolve_path('utils\ALT-236-OFF.exe'), "Starting NetFrame Control Off"),
            "browser": (self.resolve_path('utils\AnonySearch.exe'), "Starting AnonySearch"),
            "help": (self.resolve_path('utils\HELP.exe'), "Starting Help Agent"),
            "code 255": (self.resolve_path('utils\iNetwork-Analyzer.exe'), "Starting Network Analyzer"),
            "code 236": (self.resolve_path('utils\ALT-236.exe'), "Starting NetFrame Control"),
            "vault": (self.resolve_path('utils\PassGuardX-offline.exe'), "Starting PassGuard X")
        }

    def resolve_path(self, relative_path):
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, relative_path)
        
    def execute_command(self, command):
        if command in self.command_map:
            program, message = self.command_map[command]
            try:
                subprocess.Popen(program, shell=True)  # Start the program
                external_speak(message)
            except FileNotFoundError:
                external_speak("Error: {program} not found!")
            except Exception as e:
                external_speak(f"An error occurred while executing {program}: {e}")
        else:
            self.handle_fallback(command)  # Query Wolfram Alpha for general questions

    def setup_tables(self):
        """Create tables if they don't exist."""
        # Short-term memory table
        self.short_term_cursor.execute('''
            CREATE TABLE IF NOT EXISTS short_term_memory (
                timestamp INTEGER PRIMARY KEY,
                memory_data TEXT
            )
        ''')

        # Long-term memory table
        self.long_term_cursor.execute('''
            CREATE TABLE IF NOT EXISTS long_term_memory (
                key TEXT PRIMARY KEY,
                memory_data TEXT
            )
        ''')

        self.short_term_conn.commit()
        self.long_term_conn.commit()

    def load_memories(self):
        """Load memories from the short-term memory database into the in-memory list."""
        self.short_term_cursor.execute('SELECT memory_data FROM short_term_memory')
        memories = self.short_term_cursor.fetchall()
        return [memory[0] for memory in memories]

    def perceive(self, sensory_data):
        # Placeholder for handling sensory data asynchronously
        threads = []

        # Example: Threading for speech recognition
        if 'speech' in sensory_data:
            speech_thread = threading.Thread(target=self.process_speech, args=(sensory_data['speech'],))
            threads.append(speech_thread)
            speech_thread.start()

        # Example: Threading for API response handling
        if 'api_response' in sensory_data:
            api_thread = threading.Thread(target=self.process_api_response, args=(sensory_data['api_response'],))
            threads.append(api_thread)
            api_thread.start()

        # Example: Threading for system events
        if 'system_event' in sensory_data:
            system_event_thread = threading.Thread(target=self.process_system_event,
                                                   args=(sensory_data['system_event'],))
            threads.append(system_event_thread)
            system_event_thread.start()

        # Example: Threading for sensor integration
        if 'sensor_data' in sensory_data:
            sensor_thread = threading.Thread(target=self.process_sensor_data, args=(sensory_data['sensor_data'],))
            threads.append(sensor_thread)
            sensor_thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        return "Perception completed."

    def processing(self, data):
        # Placeholder for additional processing steps
        # For now, directly run SJN scheduling algorithm with example tasks
        tasks = [
            (1, 5),
            (2, 3),
            (3, 7),
            (4, 2),
            (5, 4)
        ]
        self.run_sjn(tasks)

    def run_sjn(self, tasks):
        # SJN scheduling algorithm for CPU-bound and I/O-bound tasks
        for task_id, burst_time in tasks:
            self.ready_queue.put((burst_time, task_id))

        while not self.ready_queue.empty():
            self.mutex.acquire()
            burst_time, task_id = self.ready_queue.get()
            self.mutex.release()

            # Simulate CPU-bound task
            decision = self.make_decision(task_id)
            self.execute_action(decision)

            # Simulate I/O-bound task
            io_time = random.randint(1, 3)  # Simulate random I/O wait time
            self.io_bound_task(task_id, io_time)

            # Transfer to long-term memory and update intelligence
            self.transfer_to_long_term_memory(self.short_term_memory[-1])
            self.update_intelligence(decision)

            # Provide feedback on completion
            completion_time = random.uniform(30, 180)  # Simulate completion time
            self.feedback(task_id, completion_time)

            # Notify system or trigger actions on task completion
            self.task_completed_notification(task_id)

            self.log_file = open("assistant.log", "a")

    def make_decision(self, task_id):
        # Decision-making algorithm dependent on intelligence and task_id
        if self.intelligence > 0.5:
            options = ['option1', 'option2', 'option3']
        else:
            options = ['option4', 'option5', 'option6']
        decision = random.choice(options)
        logging.error(f"Task {task_id}: Made decision {decision}")
        return decision

    def execute_action(self, decision):
        # Action execution dependent on decision and processing
        processed_decision = self.processing(decision)
        logging.error(f"Task {decision}: Executing action: {processed_decision}")
        time.sleep(1)  # Simulate action time

    @staticmethod
    def io_bound_task(task_id, io_time):
        logging.error(f"Task {task_id}: Executing I/O-bound task, waiting for {io_time} seconds.")
        time.sleep(io_time)
        logging.error(f"Task {task_id}: I/O-bound task completed.")

    def transfer_to_long_term_memory(self, recent_memory):
        # Simulate the transfer of important information to long-term memory
        key = str(time.time())  # Use timestamp as the key
        self.store_long_term_memory(key, recent_memory)
        logging.error("Information transferred to long-term memory.")

    def update_intelligence(self, decision):
        if decision.startswith('option'):
            self.intelligence += 0.1
        else:
            self.intelligence -= 0.1
        logging.error(f"Intelligence updated to {self.intelligence}")

    @staticmethod
    def feedback(task_id, completion_time):
        # Function to give feedback on tasks completed.
        if completion_time < 60:
            time_feedback = f"Great job! You completed Task '{task_id}' quickly."
        elif completion_time < 180:
            time_feedback = f"Well done! Task '{task_id}' took some time but you did it."
        else:
            time_feedback = f"It took a while, but Task '{task_id}' is completed."

        logging.info("Feedback:")
        logging.info("-" * 30)
        logging.info(f"Task: {task_id}")
        logging.info(f"Completion Time: {completion_time:.2f} seconds")
        logging.info(f"Feedback: {time_feedback}")
        logging.info("-" * 30)

    @staticmethod
    def task_completed_notification(task_id):
        # Placeholder for task completion notification to the system
        logging.info(f"Task '{task_id}' has been completed. Notifying the system...")

    def start_background_tasks(self):
        """Start background threads for reminders and automatic deletion."""
        threading.Thread(target=self.reminder_loop, daemon=True).start()
        threading.Thread(target=self.deletion_loop, daemon=True).start()

    def reminder_loop(self):
        """Periodically remind users of their stored memories."""
        while True:
            time.sleep(self.reminder_interval)
            if not self.suspended:
                self.remind_users()

    def deletion_loop(self):
        """Automatically delete all stored memories every 24 hours."""
        while True:
            time.sleep(self.deletion_interval)
            self.clear_memories()

    def run_assistant(self):
        self.wish_me()
        while True:
            if not self.suspended:
                command = self.recognize_speech()
                if command:
                    self.process_command(command)
            time.sleep(1)

    def handle_fallback(self, text):
        try:
            response = self.nlu.get_response(text)
            logging.info(f'Alpha: {response}')  # Optional: logging.info response

            # Check if the response includes a web search result with a link
            if "Would you like to open this link? (yes/no)" in response:
                external_speak("Please say yes or no.")
                # Use recognize_speech to get user response through speech
                user_response = self.recognize_speech()  # Get user response via speech recognition
                if user_response and user_response.lower() == "yes":
                    link = self.extract_link(response)
                    if link:
                        self.open_link(link)
            else:
                external_speak(response)  # Use text-to-speech to respond

        except Exception as e:
            logging.error(f"Error in fallback handling: {e}")

    def recognize_speech(self):
        last_text = ""
        command_executed = False  # Flag to track if a command was executed

        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            logging.info("Listening...")
            external_speak("I Am Listening")

            while self.listening:
                try:# Listen indefinitely for speech with a timeout of 5 seconds
                    audio = recognizer.listen(source, timeout=None)
                    

                    # Check if the audio contains speech
                    if self.is_speech(audio):
                        logging.info("Speech detected. Starting recognition...")
                        self.processing = True

                        try:
                            logging.info("Recognizing...")
                            text = recognizer.recognize_google(audio)
                            logging.info(f"User said: {text}")
                            logging.info(f'User said: {text}')

                            # Check if the command is the same as the last one
                            if text.lower() != last_text:
                                last_text = text.lower()  # Update the last command
                                command_executed = True  # Set the flag to True

                                if 'suspend' in text.lower():
                                    self.suspend_assistant()
                                elif 'unsuspend' in text.lower():
                                    self.unsuspend_assistant()
                                elif 'increase volume' in text.lower():
                                    self.change_volume('increase')
                                elif 'decrease volume' in text.lower():
                                    self.change_volume('decrease')
                                elif 'mute' in text.lower():
                                    self.change_volume('mute')
                                elif 'undo' in text.lower():
                                    self.change_volume('undo')
                                elif 'increase brightness' in text.lower():
                                    self.change_brightness('increase')
                                elif 'decrease brightness' in text.lower():
                                    self.change_brightness('decrease')
                                elif 'turn on Wi-Fi' in text.lower():
                                    self.control_wifi('turn on')
                                elif 'turn off Wi-Fi' in text.lower():
                                    self.control_wifi('turn off')
                                elif 'turn on Bluetooth' in text.lower():
                                    self.control_bluetooth('turn on')
                                elif 'turn off Bluetooth' in text.lower():
                                    self.control_bluetooth('turn off')
                                return text
                            # Reset command execution flags after processing
                            if command_executed:
                                command_executed = False
                                time.sleep(1)  # Small delay to avoid immediate reprocessing

                        except sr.UnknownValueError:
                            logging.warning("Google Speech Recognition could not understand audio")
                        except sr.RequestError as e:
                            logging.warning(f"Could not request results from Google Speech Recognition service; {e}")

                        self.processing = False
                    else:
                        logging.warning("Ignored non-speech audio")

                except sr.WaitTimeoutError:
                    # Continue listening if timeout occurs
                    continue

            return None

    @staticmethod
    def is_speech(audio, threshold=0.000001):
        # Get raw data from audio
        audio_data = np.frombuffer(audio.get_raw_data(), np.int16)

        # Normalize audio data to range [0, 1]
        audio_data = np.abs(audio_data) / 32768.0

        # Calculate the average energy of the audio data
        energy = np.mean(audio_data ** 2)

        # Consider it as speech if the energy exceeds the threshold
        return energy > threshold
    
    def extract_link(self, response):
        """Extract the link from the response text"""
        import re
        match = re.search(r"Link: (\S+)", response)
        return match.group(1) if match else None

    def open_link(self, link):
        """Open the extracted link in the web browser"""
        import webbrowser
        webbrowser.open(link)

    def main(self):
        while True:
            # Read input from stdin
            input_text = sys.stdin.readline().strip()
            if input_text:
                response = self.recognize_speech()
                # Write the response to stdout
                sys.stdout.write(response + "\n")
                sys.stdout.flush()
                # Use the speak function to provide a verbal response
                external_speak(response)

    @staticmethod
    def process_speech(speech_data):
        # Placeholder for processing speech data asynchronously
        logging.info(f"Processing speech data: {speech_data}")

    @staticmethod
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def process_speech_command(self, command):
        logging.info(f"Processing speech command: {command}")
        if "calculate" in command:
            self.calculate(command)
        elif "website" in command:
            self.open_website(command)
        elif "search for" in command:
            self.search_web(command)
        elif "tell me about" in command:
            self.tell_about(command)
        elif "suspend" in command:
            self.suspend_assistant()
        elif "unsuspend" in command:
            self.unsuspend_assistant()
        elif "set alarm to" in command:
            self.set_alarm(command)
        elif "power off" in command:
            self.shutdown()
        elif "sleep" in command:
            self.sleep()
        elif "time" in command:
            self.get_time()
        # Example: Get current date
        elif "date" in command:
            self.get_date()
        elif "News" in command:
            self.fetch_and_display_news()
        # Handle command "alpha hibernate for [duration]"
        elif "hibernate" in command:
            try:
                # Define a regular expression pattern to match durations like "for 5 minutes" or "for 10 seconds"
                duration_pattern = r'for (\d+) (seconds?|minutes?)'

                # Use regular expression to find duration in the command
                match = re.search(duration_pattern, command)

                if match:
                    duration_value = int(match.group(1))  # Extract the numeric value of duration
                    unit = match.group(2)  # Extract the unit of duration (seconds or minutes)

                    # Convert duration to seconds based on the unit
                    if unit.startswith('minute'):
                        sleep_duration = duration_value * 60
                    elif unit.startswith('second'):
                        sleep_duration = duration_value
                    else:
                        logging.warning("Unknown unit specified.")
                        external_speak("Unknown unit specified.")
                        return

                    self.go_to_sleep(command)
                else:
                    logging.error("Command not recognized.")
                    external_speak("Command not recognized.")

            except ValueError:
                logging.error("Invalid command format for sleep duration.")
                external_speak("Invalid command format for sleep duration.")
        elif "maps" in command:
            self.open_maps()
        elif "exit" in command:
            self.exit()
        elif "install " in command:
            self.install_application(command)
        elif "clear mem" in command:
            self.clear_memories(command)
        elif "clear memory" in command:
            self.clear_memories(command)
        elif command.startswith("ask alpha"):
            query = command[len("ask Wolfram"):].strip()  # Extract the query
            self.ask_wolfram(query)
        elif command.startswith("ask Alpha"):
            query = command[len("ask Wolfram"):].strip()  # Extract the query
            self.ask_wolfram(query)
        elif 'open' in command.lower():
            # Use regular expression to extract application name after "open"
            match = re.search(r'open\s+(.+)', command, re.IGNORECASE)
            if match:
                application_name = match.group(1).strip().replace(" ", "_")  # Extract and normalize application name
                self.access_application_or_install('access', application_name)
            else:
                logging.error("Invalid command format.")
        else:
            self.secondary_command(command)  # Query Wolfram Alpha for general questions


    @staticmethod
    def calculate(command):
        # Calculate mathematical expression using Wolfram Alpha
        expression = command.replace("calculate", "").strip()
        
        try:
            # Query Wolfram Alpha
            res = wolfram_alpha_client.query(expression)
            
            # Check if results are available
            if res.results:
                try:
                    # Attempt to get the result
                    answer = next(res.results).text
                except StopIteration:
                    # Handle the case where results are exhausted
                    answer = "Sorry, I couldn't calculate that."
            else:
                # Handle the case where there are no results
                answer = "Sorry, I couldn't calculate that."
        
        except Exception as e:
            # Handle any other exceptions that might occur
            answer = f"An error occurred: {str(e)}"
        
        logging.info(f"Calculation result: {answer}")
        external_speak(answer)


    @staticmethod
    def calculate_wolfram(query):
        res = wolfram_alpha_client.query(query)
        answer = next(res.results).text
        return answer

    @staticmethod
    def open_website(command):
        # Open a website based on user command
        website = re.search('website (.+)', command).group(1)
        url = f"https://www.{website}.com"
        webbrowser.open(url)
        logging.info(f"Opening website: {url}")

    @staticmethod
    def search_web(command):
        # Search the web using user command
        query = re.search('search for (.+)', command).group(1)
        url = f"https://www.google.com/search?q={quote(query)}"
        webbrowser.open(url)
        logging.info(f"Searching the web for: {query}")

    @staticmethod
    def tell_about(command):
        topic = re.search(r'tell me about (.+)', command).group(1)
        try:
            summary = wikipedia.summary(topic, sentences=2)
            logging.info(f"Here is what I found about {topic}: {summary}")
            external_speak(summary)
        except wikipedia.exceptions.DisambiguationError as e:
            logging.error(f"DisambiguationError: {e}")
            external_speak("There were multiple matches. Please be more specific.")
        except wikipedia.exceptions.PageError as e:
            logging.error(f"PageError: {e}")
            external_speak("I could not find any information on that topic.")

    def remember_this(self, command):
        try:
            # Extract memory data from the command
            memory_data = self.extract_memory_data(command)

            # Store memory data in short-term memory database
            self.store_short_term_memory(memory_data)

            # Log memory data
            self.log_memory(memory_data)

            # Confirm memory storage to user
            self.confirm_memory_storage()

            # Ask if the user wants to store in long-term memory via speech
            external_speak("Do you want to store this in long-term memory? Please say yes or no.")

            # Use speech recognition to capture the response
            user_input = self.get_speech_input()

            if user_input == 'yes':
                # Store in long-term memory
                self.store_long_term_memory(memory_data)
                external_speak("Memory has been stored in long-term memory.")
            else:
                external_speak("Memory was not stored in long-term memory, only in short-term memory.")
                
            # Update in-memory list of memories
            self.update_memories(memory_data)

        except Exception as e:
            logging.error(f"An error occurred while processing the command: {e}")

    def get_speech_input(self):
        """Use speech recognition to get a response from the user."""
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            logging.info("Listening for response...")
            audio = recognizer.listen(source)
            try:
                # Convert speech to text
                response = recognizer.recognize_google(audio).lower()
                logging.info(f"User said: {response}")
                return response
            except sr.UnknownValueError:
                external_speak("Sorry, I could not understand your response. Please try again.")
                return self.get_speech_input()  # Retry if speech is unclear
            except sr.RequestError as e:
                external_speak(f"Could not request results; {e}")
                return 'no'  # Default to 'no' if there is a speech recognition issue
        return None

    @staticmethod
    def extract_memory_data(command):
        """Extract the memory data from the command."""
        return command.split("remember", 1)[-1].strip()

    def store_short_term_memory(self, memory_data):
        """Store the memory data in short-term memory in the SQLite database."""
        timestamp = int(time.time())  # Use current timestamp as primary key
        self.short_term_cursor.execute('''
            INSERT INTO short_term_memory (timestamp, memory_data) 
            VALUES (?, ?)
        ''', (timestamp, memory_data))
        self.short_term_conn.commit()

    @staticmethod
    def log_memory(memory_data):
        """Log the memory to the console or a file."""
        logging.info(f"Memory Stored: {memory_data}")

    def confirm_memory_storage(self):
        """Confirm that the memory was stored successfully."""
        external_speak("Your memory has been stored successfully.")

    def update_memories(self, memory_data):
        """Update the in-memory list of memories."""
        if 'memories' not in self.__dict__:
            self.memories = []
        self.memories.append(memory_data)

    def remind_users(self):
        """Remind users of all stored memories."""
        if self.memories:
            for memory in self.memories:
                external_speak(f"Remember this: {memory}")

    def clear_memories(self, command):
        """Clear all stored memories."""
        self.memories.clear()
        self.short_term_cursor.execute('DELETE FROM short_term_memory')
        self.long_term_cursor.execute('DELETE FROM long_term_memory')
        self.short_term_conn.commit()
        self.long_term_conn.commit()
        external_speak("All stored memories have been deleted.")

    def suspend_assistant(self):
        self.suspended = True
        external_speak("Assistant suspended.")
        logging.info("Assistant is suspended.")
        self.listen_for_unsuspend()

    def tell_joke(self, command):
        joke = pyjokes.get_joke()
        external_speak(joke)

    def unsuspend_assistant(self):
        self.suspended = False
        external_speak("Assistant activated.")
        logging.info("Assistant is active.")

    def listen_for_unsuspend(self):
        """Listen for the 'unsuspend' command while the assistant is suspended."""
        while self.suspended:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source)

            try:
                text = recognizer.recognize_google(audio)
                logging.info(f"User said: {text}")
                logging.info(f'User said: {text}')

                if 'unsuspend' in text.lower():
                    self.unsuspend_assistant()
            except sr.UnknownValueError:
                logging.error(f"Could not Recognize speeach.")
            except sr.RequestError as e:
                logging.error(f"Could not request results from Google Speech Recognition service; {e}")

            time.sleep(1)  # Small delay to prevent excessive CPU usage

    def recall_memories(self):
        """Recall and possibly speak out all stored memories from short-term and long-term memory."""
        if self.memories:
            external_speak("Here are the memories I have from short-term memory:")
            for index, memory in enumerate(self.memories, start=1):
                external_speak(f"Memory {index}: {memory}")
        else:
            external_speak("I don't seem to have any short-term memories right now.")

        # Recall long-term memories
        self.long_term_cursor.execute('SELECT memory_data FROM long_term_memory')
        long_term_memories = self.long_term_cursor.fetchall()
        if long_term_memories:
            external_speak("Here are the memories I have from long-term memory:")
            for index, memory in enumerate(long_term_memories, start=1):
                external_speak(f"Long-Term Memory {index}: {memory[0]}")
        else:
            external_speak("I don't have any long-term memories right now.")

    @staticmethod
    def shutdown():
        logging.info("Shutting down...")
        # Perform shutdown actions here if needed
        os.system("shutdown /s /t 1")

    def exit(self):
        """Shutdown assistant (exit program)."""
        try:
            external_speak("Shutting down assistant.")  # Announce shutdown
            self.log_file.close()  # Close log file if it's open
            
            # Close the window (UI)
            if hasattr(self, 'window') and window is not None:
                window.close()  # Close the UI window
            
            # Terminate the program gracefully
            logging.info("Shutting down the assistant.")
            exit()  # Exit the program
            
        except Exception as e:
            logging.error(f"Error while shutting down: {e}")
            exit(1)  # Exit with error code in case of failure

    def active(self):
        while True:
            if not self.active:
                self.unsuspend_assistant()
            else:
                self.suspend_assistant()
            time.sleep(1)

    def hibernate(self, command):
        try:
            # Extract the duration from the command
            match = re.search(r'hibernate for (\d+) (seconds|minutes|hours)', command)
            if not match:
                raise ValueError("Command format is incorrect. Expected format: 'hibernate for <duration> <unit>'.")

            duration_value = int(match.group(1))
            duration_unit = match.group(2)

            # Convert the duration to seconds for sleep function
            if duration_unit == "minutes":
                duration_value *= 60
            elif duration_unit == "hours":
                duration_value *= 3600
            elif duration_unit != "seconds":
                raise ValueError(f"Unsupported unit of time: {duration_unit}")

            logging.info(f"Hibernating for {duration_value} seconds...")
            external_speak(f"Hibernating for {duration_value} seconds...")
            self.is_sleeping = True
            self.sleep_event.clear()
            time.sleep(duration_value)
            self.is_sleeping = False
            logging.info("Hibernation complete.")
            external_speak(
                f"Hibernation for {duration_value // 60} minutes is complete.")  # Converted to minutes for speech

        except ValueError as ve:
            logging.warning(f"Invalid command format: {ve}")
            external_speak(
                "I'm sorry, I didn't catch that. Please specify the duration and unit in the correct format.")
        except Exception as e:
            logging.error(f"Error hibernating: {e}")
            external_speak("Sorry, there was an error hibernating.")

    @staticmethod
    def sleep():
        logging.info("Going to sleep...")
        # Perform sleep actions here if needed
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    @staticmethod
    def get_time():
        current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
        logging.info(f"The current time is {current_time}")
        external_speak(f"The current time is {current_time}")

    @staticmethod
    def get_date():
        year = datetime.datetime.now().year
        month = datetime.datetime.now().strftime("%B")
        day = datetime.datetime.now().day
        logging.info(f"Today is {month} {day}, {year}")
        external_speak(f"Today is {month} {day}, {year}")

    @staticmethod
    def ask_wolfram(query):
        try:
            res = wolfram_alpha_client.query(query)
            answer = next(res.results).text
            logging.info(f"Wolfram Alpha says: {answer}")
            external_speak(answer)
        except Exception as e:
            logging.error(f"Error fetching results from Alpha: {str(e)}")
            external_speak("Sorry, I couldn't fetch the answer for you.")

    @staticmethod
    def wish_me():
        hour = datetime.datetime.now().hour
        if 6 <= hour < 12:
            external_speak("Good morning Sir!")
        elif 12 <= hour < 18:
            external_speak("Good afternoon Sir!")
        elif 18 <= hour < 24:
            external_speak("Good evening Sir!")
        else:
            external_speak("Hello!")

        external_speak("Alpha At your service. How may I assist you?")

    def process_command(self, command):
        # Handle specific commands
        if 'time' in command:
            self.get_time()
        elif "close" in command:
            self.cleanup(command)
        elif 'date' in command:
            self.get_date()
        elif 'remember' in command:
            # Extract the memory data from the command
            memory_data = command.split('remember', 1)[-1].strip()
            self.remember_this(memory_data)
        elif 'recall' in command:
            self.recall_memories()
        elif 'access' in command or 'install' in command:
            # Use regular expression to extract application name after "install"
            match = re.search(r'install\s+(.+)', command, re.IGNORECASE)
            if match:
                application_name = match.group(1).strip().replace(" ", "_")  # Extract and normalize application name
                self.install_application(command)
                self.install_application_winget(command)
        elif 'download' in command.lower():
            # Extract the part of the command after 'download'
            parts = command.lower().split('download', 1)
            if len(parts) > 1:
                app_name = parts[1].strip()
                if app_name:
                    self.search_and_download(app_name)
                else:
                    logging.warning("No application name was provided after 'download'.")
            else:
                logging.warning("No application name found in the command.")
        elif 'news' in command:
            # Extract the command after 'news'
            match = re.search(r'news\s*(.+)?', command, re.IGNORECASE)
            if match:
                news_command = match.group(1)  # This captures the words after 'news'
                # Process the news command here (e.g., fetching news based on news_command)
                self.fetch_and_display_news(news_command)
        elif 'maps' in command.lower():
            # Split command to find the part after 'maps'
            parts = command.lower().split('maps', 1)
            if len(parts) > 1:
                location = parts[1].strip()
                
                if location:
                    # Construct the Google Maps URL with the search query
                    search_query = quote(location)
                    map_url = f"https://www.google.com/maps/search/?api=1&query={search_query}"
                    
                    # Open the map URL in a web browser
                    webbrowser.open(map_url)
                else:
                    logging.warning("No location was provided after 'maps'.")
            else:
                logging.warning("No location found in the command.")
        elif "open" in command.lower():
            match = re.search(r'open\s+(.+)', command, re.IGNORECASE)
            if match:
                application_name = match.group(1).strip()  # Extract application name
                self.open_existing_application(application_name)
            else:
                logging.warning("Invalid command format.")
                external_speak("Invalid command format.")

        else:
            self.process_speech_command(command)

    def log_message(self, message):
        # Log messages to a file
        self.log_file.write(f"{datetime.datetime.now()}: {message}\n")
        self.log_file.flush()

    def close_log(self):
        # Close the log file
        self.log_file.close()

    def assess_complexity(self, command):
        """
        Assess the complexity of the command.
        This is a placeholder for complexity assessment logic.
        For example, you might check for the length of the command,
        the presence of specific keywords, or other factors.
        """
        # Placeholder complexity calculation logic
        complexity_score = len(command)  # Simple example: use command length as a proxy for complexity

        # Set a threshold value for complexity; this value is just an example
        self.COMPLEXITY_THRESHOLD = 50  # Define this value based on your needs
        
        return complexity_score
    
    def secondary_command(self, command):
        complexity = self.assess_complexity(command)
        if complexity > self.COMPLEXITY_THRESHOLD:
            Brain.ask_wolfram(command)  # Correctly call the static method
        elif 'play' in command:
            self.handle_music_command(command)
        elif 'increase volume' in command:
            self.change_volume('increase')
        elif 'decrease volume' in command:
            self.change_volume('decrease')
        elif 'mute' in command:
            self.change_volume('mute')
        elif 'restore audio' in command:
            self.change_volume('restore audio')
        elif 'increase brightness' in command:
            self.change_brightness('increase')
        elif 'decrease brightness' in command:
            self.change_brightness('decrease')
        elif 'turn on Wi-Fi' in command:
            self.control_wifi('turn on')
        elif 'turn off Wi-Fi' in command:
            self.control_wifi('turn off')
        elif 'turn on Bluetooth' in command:
            self.control_bluetooth('turn on')
        elif 'turn off Bluetooth' in command:
            self.control_bluetooth('turn off')
        elif 'tell me a joke' in command:
            self.tell_joke(command)
        else:
            self.execute_command(command)
            
    def change_volume(self, action):
        # Fixed volume increment/decrement
        amount = 10000  # This is equivalent to 10 units in nircmd

        if action == 'increase':
            subprocess.run(["nircmd.exe", "changesysvolume", str(amount)])
            logging.info("Volume increased by 10 units")
            external_speak("Volume Increased")
        elif action == 'decrease':
            subprocess.run(["nircmd.exe", "changesysvolume", str(-amount)])
            logging.info("Volume decreased by 10 units")
            external_speak("Volume Decreased")
        elif action == 'mute':
            subprocess.run(["nircmd.exe", "mutesysvolume", "1"])
            external_speak("Sound is muted")
        elif action == 'restore audio':
            subprocess.run(["nircmd.exe", "mutesysvolume", "0"])
            external_speak("Sound is unmuted")
        else:
            external_speak("Invalid action. Use 'increase', 'decrease', 'mute', or 'restore audio'.")

    def change_brightness(self, action):
        # Fixed brightness increment/decrement
        amount = 10  # Amount to change brightness (can be adjusted)

        if action == 'increase':
            subprocess.run(["nircmd.exe", "changebrightness", str(amount)])
            logging.info("Brightness increased by 10 units")
            external_speak("Brightness Increased")
        elif action == 'decrease':
            subprocess.run(["nircmd.exe", "changebrightness", str(-amount)])
            logging.info("Brightness decreased by 10 units")
            external_speak("Brightness Decreased")
        else:
            external_speak("Invalid action. Use 'increase' or 'decrease'.")

    def control_wifi(self, action):
        if action == 'turn on':
            command = 'Enable-NetAdapter -Name "Wi-Fi" -Confirm:$false'
        elif action == 'turn off':
            command = 'Disable-NetAdapter -Name "Wi-Fi" -Confirm:$false'
        else:
            external_speak("Invalid action. Use 'turn on' or 'turn off'.")
            return

        try:
            # Execute PowerShell command with elevated privileges
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    f"Start-Process powershell -ArgumentList '-NoProfile -Command \"{command}\"' -Verb RunAs"
                ],
                check=True
            )
            external_speak(f"Wi-Fi has been {action}")
        except subprocess.CalledProcessError as e:
            external_speak(f"Failed to {action} Wi-Fi. Error: {e}")

    def control_bluetooth(self, action):
        try:
            # Initialize WMI service
            wmi_service = win32com.client.GetObject("winmgmts:\\\\.\\root\\cimv2")
            # Query for Bluetooth devices
            query = "SELECT * FROM Win32_PnPEntity WHERE Name LIKE '%Bluetooth%'"
            devices = wmi_service.ExecQuery(query)
            
            if not devices:
                logging.info("No Bluetooth devices found.")
                return
            
            for device in devices:
                # Check if device is already enabled or disabled
                if action == "turn on" and "Disabled" in device.Status:
                    device.Enable()  # Ensure Enable() is called correctly as a method
                    logging.info(f"Bluetooth device '{device.Name}' has been turned on.")
                elif action == "turn off" and "OK" in device.Status:
                    device.Disable()  # Ensure Disable() is called correctly as a method
                    logging.info(f"Bluetooth device '{device.Name}' has been turned off.")
                else:
                    logging.info(f"Bluetooth device '{device.Name}' is already {action}.")
        except Exception as e:
            logging.error(f"Failed to {action} Bluetooth. Error: {e}")

    def set_alarm(self, command):
        logging.info(f'set_alarm called with command: {command}')  # Debugging statement

        # Check if the command has already been processed
        if command in self.processed_commands:
            logging.info("Command already processed.")
            return
        
        match = re.search(r'set alarm to (\d{1,2}:\d{2} (?:a\.m\.|p\.m\.))', command, re.IGNORECASE)
        if match:
            alarm_time = match.group(1)
            self.alarm_time_12 = alarm_time
            self.alarm_time_24 = self.convert_to_24_hour_format(alarm_time)
            if self.alarm_time_24:
                logging.info(f"Alarm set for {alarm_time}")
                external_speak(f"Alarm set for {alarm_time}")
                self.alarm_set = True
                self.processed_commands.add(command)  # Mark this command as processed
                # Start the alarm clock in a new thread
                threading.Thread(target=self.alarm_clock, daemon=True).start()
            else:
                logging.warning("Invalid time format.")
                external_speak("Invalid time format.")
        else:
            logging.warning("Please say the alarm time in the correct format (e.g., 07:30 a.m. or 07:30 p.m.).")
            external_speak("Please say the alarm time in the correct format (e.g., 07:30 a.m. or 07:30 p.m.).")

    def set_alarm_thread(self, command):
        logging.warning("set_alarm_thread called with command:", command)  # Debugging statement
        # Use a lock to ensure thread safety when accessing processed_commands
        with threading.Lock():
            threading.Thread(target=self.set_alarm, args=(command,), daemon=True).start()

    @staticmethod
    def convert_to_24_hour_format(alarm_time):
        match = re.match(r'(\d{1,2}):(\d{2}) (a\.m\.|p\.m\.)', alarm_time, re.IGNORECASE)
        if match:
            hour, minute, period = int(match.group(1)), int(match.group(2)), match.group(3).lower()
            if period == 'p.m.' and hour != 12:
                hour += 12
            elif period == 'a.m.' and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"
        return None

    def alarm_clock(self):
        """Function to set off an alarm at the specified time."""
        logging.info("Alarm clock thread started")  # Debugging statement
        while self.alarm_set:
            current_time = datetime.datetime.now().strftime("%H:%M")  # Current time in 24-hour format
            if current_time == self.alarm_time_24:
                logging.info("Time to wake up!")
                self.alarm_triggered.set()  # Set the event flag
                self.play_alarm_sound()
                self.alarm_set = False  # Disable the alarm after it goes off
                break
            time.sleep(60)

    def play_alarm_sound(self):
        if self.alarm_sound_file:
            try:
                sound = AudioSegment.from_file(self.alarm_sound_file)
                play(sound)
            except Exception as e:
                logging.error(f"Error playing sound: {e}")
        else:
            logging.error("No alarm sound file set.")

    def check_alarm(self):
        """This function runs in the main thread and checks if the alarm has triggered."""
        logging.warning("Checking alarm...")  # Debugging statement
        while True:
            self.alarm_triggered.wait()  # Wait until the event flag is set
            external_speak("Time to wake up!")
            self.alarm_triggered.clear()  # Reset the event flag for the next alarm

    def get_youtube_video_url(self, query):
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()
        if results['result']:
            video_url = results['result'][0]['link']
            return video_url
        return None

    def play_music(self, platform, music_name):
        if platform.lower() == "spotify":
            results = self.sp.search(q=music_name, limit=1, type="track")
            if results['tracks']['items']:
                track_uri = results['tracks']['items'][0]['uri']
                try:
                    self.sp.start_playback(uris=[track_uri])
                    logging.info(f"Playing '{music_name}' on Spotify.")
                except spotipy.exceptions.SpotifyException as e:
                    logging.error(f"Error starting playback: {e}")
            else:
                logging.error(f"Could not find '{music_name}' on Spotify.")

        elif platform.lower() == "youtube":
            search_query = f"{music_name} music"
            video_url = self.get_youtube_video_url(search_query)

            if video_url:
                webbrowser.open(video_url)
                logging.info(f"Playing '{music_name}' on YouTube.")
            else:
                logging.info(f"Could not find '{music_name}' on YouTube.")

    def handle_music_command(self, text):
        parts = text.lower().split(" on ")
        if len(parts) == 2:
            music_name = parts[0].replace("play", "").strip()
            platform = parts[1].strip()
            self.play_music(platform, music_name)

    @staticmethod
    def access_application_or_install(action, application_name):
        try:
            if action == 'access':
                # Handle application access based on the platform
                if platform.system() == 'Windows':
                    if application_name.lower() == 'chrome':
                        subprocess.Popen(['start', 'chrome'], shell=True)
                    elif application_name.lower() == 'firefox':
                        subprocess.Popen(['start', 'firefox'], shell=True)
                    elif application_name.lower() == 'edge':
                        subprocess.Popen(['start', 'microsoft-edge:'], shell=True)
                    elif application_name.lower() == 'ie' or application_name.lower() == 'internet explorer':
                        subprocess.Popen(['start', 'iexplore'], shell=True)
                    elif application_name.lower() == 'notepad':
                        subprocess.Popen(['start', 'notepad'], shell=True)
                    elif application_name.lower() == 'calculator':
                        subprocess.Popen(['start', 'calc'], shell=True)
                    elif application_name.lower() == 'explorer' or application_name.lower() == 'file explorer':
                        subprocess.Popen(['start', 'explorer'], shell=True)
                    elif application_name.lower() == 'control panel':
                        subprocess.Popen(['start', 'control'], shell=True)
                    elif application_name.lower() == 'task manager':
                        subprocess.Popen(['start', 'taskmgr'], shell=True)
                    elif application_name.lower() == 'settings' or application_name.lower() == 'windows settings':
                        subprocess.Popen(['start', 'ms-settings:'], shell=True)
                    # Add more applications as needed
                    else:
                        logging.error(f"Error: Application '{application_name}' not supported or recognized on Windows.")
                        external_speak(
                            f"Error: Application '{application_name}' not supported or recognized on Windows.")

                elif platform.system() == 'Darwin':  # macOS
                    if application_name.lower() == 'chrome':
                        subprocess.Popen(['open', '-a', 'Google Chrome'])
                    elif application_name.lower() == 'firefox':
                        subprocess.Popen(['open', '-a', 'Firefox'])
                    # Add more applications as needed
                    else:
                        logging.error(f"Error: Application '{application_name}' not supported or recognized on macOS.")

                elif platform.system() == 'Linux':
                    if application_name.lower() == 'chrome':
                        subprocess.Popen(['google-chrome'])
                    elif application_name.lower() == 'firefox':
                        subprocess.Popen(['firefox'])
                    # Add more applications as needed
                    else:
                        logging.error(f"Error: Application '{application_name}' not supported or recognized on Linux.")

                else:
                    logging.error(
                        f"Error: Unsupported platform '{platform.system()}'. Cannot access application '{application_name}'.")

            elif action == 'install':
                # Implement logic to install the specified application
                pass  # Placeholder for installation logic

        except Exception as e:
            logging.error(f"Error handling '{action}' for application '{application_name}': {str(e)}")

    @staticmethod
    def open_existing_application(application_name):
        try:
            os_system = platform.system()  # Get the operating system
            application_name = application_name.lower()

            if os_system == 'Windows':
                applications = {
                    'chrome': 'chrome',
                    'firefox': 'firefox',
                    'edge': 'microsoft-edge:',
                    'ie': 'iexplore',
                    'internet explorer': 'iexplore',
                    'notepad': 'notepad',
                    'calculator': 'calc',
                    'explorer': 'explorer',
                    'file explorer': 'explorer',
                    'control panel': 'control',
                    'task manager': 'taskmgr',
                    'settings': 'ms-settings:',
                    'windows settings': 'ms-settings:'
                }
                command = applications.get(application_name)
                if command:
                    subprocess.Popen(['start', command], shell=True)
                    logging.info(f"Opening {application_name}.")
                    external_speak(f"Opening {application_name}.")
                else:
                    logging.error(f"Error: Application '{application_name}' not supported or recognized on Windows.")
                    external_speak(f"Error: Application '{application_name}' not supported or recognized on Windows.")

            elif os_system == 'Darwin':  # macOS
                applications = {
                    'chrome': 'Google Chrome',
                    'firefox': 'Firefox',
                    'safari': 'Safari'
                }
                app_name = applications.get(application_name)
                if app_name:
                    subprocess.Popen(['open', '-a', app_name])
                    logging.info(f"Opening {application_name}.")
                    external_speak(f"Opening {application_name}.")
                else:
                    logging.error(f"Error: Application '{application_name}' not supported or recognized on macOS.")
                    external_speak(f"Error: Application '{application_name}' not supported or recognized on macOS.")

            elif os_system == 'Linux':
                applications = {
                    'chrome': 'google-chrome',
                    'firefox': 'firefox'
                }
                command = applications.get(application_name)
                if command:
                    subprocess.Popen([command])
                    logging.info(f"Opening {application_name}.")
                    external_speak(f"Opening {application_name}.")
                else:
                    logging.error(f"Error: Application '{application_name}' not supported or recognized on Linux.")
                    external_speak(f"Error: Application '{application_name}' not supported or recognized on Linux.")

            else:
                logging.error(f"Error: Unsupported platform '{os_system}'. Cannot open application '{application_name}'.")
                external_speak(
                    f"Error: Unsupported platform '{os_system}'. Cannot open application '{application_name}'.")

        except Exception as e:
            logging.error(f"Error opening application '{application_name}': {str(e)}")
            external_speak(f"Error opening application '{application_name}': {str(e)}")

    @staticmethod
    def install_application(command):
        # Example: Install application using subprocess
        application_name = re.search(r'install (.+)', command).group(1)
        try:
            subprocess.run(['winget', 'install', application_name], check=True)
            external_speak(f"{application_name} has been installed.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error installing application: {e}")
            external_speak(f"There was an error installing {application_name}.")

    @staticmethod
    def fetch_and_display_news(news_category=None):
        try:
            # Check if a news category was provided; if not, default to general news
            if news_category:
                # Open the news category URL in the default web browser
                google_news_url = f'https://news.google.com/{news_category}'
                webbrowser.open(google_news_url, new=2)
                logging.info(f"Opening {news_category} news in the browser.")
                external_speak(f"Opening {news_category} news in the browser.")
            else:
                # Fetch news from Google News RSS feed
                url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
                response = requests.get(url)
                content = response.content
                soup = BeautifulSoup(content, "html.parser")
                articles = soup.findAll("item")

                # Construct the news summary
                speak_news = "The news for today are as follows:"
                for i, article in enumerate(articles, start=1):
                    if i > 5:  # Limit to top 5 news articles
                        break
                    title = article.find("title").text
                    speak_news += f" {i}. {title}. "

                # Speak out the news summary
                external_speak(speak_news)
                logging.info(speak_news)

        except Exception as e:
            logging.error(f"Error: {e}")
            external_speak(f"An error occurred while fetching the news: {e}")

    @staticmethod
    def open_news_in_browser(news_category):
        # Define the Google News URL based on the news category
        google_news_url = f'https://news.google.com/{news_category}'

        try:
            # Open the news URL in the default web browser
            webbrowser.open(google_news_url, new=2)

        except Exception as e:
            logging.error(f"Error opening news in browser: {e}")
    
    def short_term_memory(self):
        # Retrieve short-term memory from SQLite database
        self.short_term_cursor.execute("SELECT * FROM short_term_memory ORDER BY timestamp DESC LIMIT 1")
        result = self.short_term_cursor.fetchone()
        if result:
            return json.loads(result[1])['text']
        else:
            return ""

    def wake(self):
        """Wake up the assistant immediately."""
        if self.is_sleeping:
            logging.info("Waking up the assistant...")
            external_speak("Waking up now...")
            self.is_sleeping = False
            self.sleep_event.set()  # Ensure that any waiting on the sleep event is notified
        else:
            logging.info("The assistant is already awake.")
            external_speak("I am already awake.")

    def listen_for_wake_word(self):
        """Continuously listen for the wake word."""
        while self.is_sleeping:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source)
                logging.info("Listening for wake word...")
                external_speak("Listening for wake word...")  # Notify that it's listening

                audio = recognizer.listen(source)

            try:
                logging.info("Recognizing...")
                text = recognizer.recognize_google(audio)
                logging.info(f"User said: {text}")
                logging.info(f'User said: {text}')

                if 'wake' in text.lower():
                    self.wake()  # Wake the assistant up
            except sr.UnknownValueError:
                logging.info("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                logging.info(f"Could not request results from Google Speech Recognition service; {e}")

        # Sleep briefly to avoid high CPU usage
        time.sleep(1)

    def store_long_term_memory(self, memory_data):
        """Store the memory data in long-term memory in the SQLite database."""
        # Use a unique key for long-term memory, could be a hash or custom key
        key = str(int(time.time()))  # Example: using timestamp as key
        self.long_term_cursor.execute('''
            INSERT INTO long_term_memory (key, memory_data) 
            VALUES (?, ?)
        ''', (key, memory_data))
        self.long_term_conn.commit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())

