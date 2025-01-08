from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
import sys

arguments = sys.argv

service = Service(executable_path="./chromedriver")
driver = webdriver.Chrome(service=service)

driver.get(arguments[1])
login_button = driver.find_element(By.ID, "solo-login-btn")
login_button.click()

username = driver.find_element(By.ID, "username")
password = driver.find_element(By.ID, "password")

username.send_keys(arguments[2])
password.send_keys(arguments[3])

login_button = driver.find_element(By.CLASS_NAME, "login-page-primary-button")
login_button.click()

time.sleep(1)

login_button = driver.find_element(By.CLASS_NAME, "login-page-primary-button")
login_button.click()
time.sleep(60)

driver.quit()