from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from helper_functions import btn_click_classname, btn_click_css_selector, btn_click_xpath_selector, scrape_account_transactions
import csv_module
import time
import os

# Remove old file used for keeping track of the current month
if(os.path.isfile("demofile2.txt")):
    os.remove("demofile2.txt")

# Create base template csv with headers
csv_module.create_csv()

options = Options()
download_dir = os.path.join(os.getcwd(), "images") # Changing default chrome download directory for files

prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True
}

options.add_experimental_option("prefs", prefs)

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

selected_months = driver.find_elements(By.XPATH, '/html/body/div[1]/div[1]/div[2]/div/div/div[2]')
# Open file to write output
with open("demofile2.txt", "a") as f:
    for month in selected_months:
        # Get text of each element
        print(month.text)
        f.write(month.text + "\n")  # Adding newline for separation
        
        # Wait until the element is clickable
        try:
            month_button = month.find_element(By.XPATH, './/button')  # Use relative XPath to find the button within 'month'

            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(month_button))
            # Perform the click
            month_button.click()
            print(f"Clicked on: {month.text}")

            try:
                wait = WebDriverWait(driver, 4)

                wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]/div/div[2]/div[1]/div/div/div/div[3]')))
                all_sales = month.find_elements(By.CSS_SELECTOR, 'div.list-item.status-ok.clickable')
                print(f"Count of items: {len(all_sales)}")

                for sale in range(len(all_sales)):
                    try:
                        print(f"Current_sale: {sale}")
                        time.sleep(2)
                        current_sales = driver.find_elements(By.CSS_SELECTOR, 'div.list-item.status-ok.clickable')
                        time.sleep(2)
                        print(f"Text value: {current_sales[sale].text}")
                        current_sales[sale].click()
                        data = scrape_account_transactions(driver, By, csv_module)  # Reads the table data and downloads file if available
                        time.sleep(10)
                        driver.back()
                    except Exception:
                        print("Something went wrong here with", sale)

            except Exception as e:
                print(f"Failed to click items: {e}")
            
            WebDriverWait(driver, 5).until(EC.staleness_of(month))  # waits for the element to no longer be in the DOM
            
        except Exception as e:
            print(f"Failed to click on element {month.text}: {e}")


time.sleep(300)

driver.quit()
