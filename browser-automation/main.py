from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from helper_functions import btn_click_classname, btn_click_css_selector, btn_click_xpath_selector
from documents import get_documents
from csv_module import Csv
from transactions import transactions_data
import time
import os

# Remove old file used for keeping track of the current month
if os.path.isfile("demofile2.txt"):
    os.remove("demofile2.txt")

options = Options()
download_dir = os.path.join(os.getcwd(), "images") # Changing default chrome download directory for files

prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True
}

options.add_experimental_option("prefs", prefs)
#options.add_argument("--headless=new") # Disables browser taking focus while running the script

# Reading file with url, credentials, etc.
with open('../myStuff.txt') as f:
    lines = [line for line in f]


arguments = lines

service = Service(executable_path="./chromedriver")
driver = webdriver.Chrome(service=service, options=options)
driver.maximize_window()

driver.get(arguments[0])
login_button = driver.find_element(By.ID, "solo-login-btn")
login_button.click()

username = driver.find_element(By.ID, "username")
password = driver.find_element(By.ID, "password")

username.send_keys(arguments[1])
password.send_keys(arguments[2])

btn_click_classname(driver, By, time, "login-page-primary-button")

btn_click_classname(driver, By, time, "login-page-primary-button")

btn_click_css_selector(driver, By, time, "button.dashboard-show-bank-statement")

selected_months = driver.find_elements(By.CSS_SELECTOR, 'div.month-timeline-item.completed.hideEvents')
# Open file to write output

# Gets all transaction data and stores them in csv's and images folder under correct months
transactions_data(driver, By, WebDriverWait, EC, time, selected_months, Csv)

time.sleep(60)

# Gets all documents and sorts them by year by adding them to directories
get_documents(driver, By, time, WebDriverWait, EC)

time.sleep(60)

driver.quit()
