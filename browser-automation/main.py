from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
import sys

# Empty old file
f = open("demofile2.txt", "a")
f.truncate(0)
f.close()

from helper_functions import btn_click_classname, btn_click_css_selector

arguments = sys.argv

service = Service(executable_path="./chromedriver")
driver = webdriver.Chrome(service=service)
driver.maximize_window()

driver.get(arguments[1])
login_button = driver.find_element(By.ID, "solo-login-btn")
login_button.click()

username = driver.find_element(By.ID, "username")
password = driver.find_element(By.ID, "password")

username.send_keys(arguments[2])
password.send_keys(arguments[3])

btn_click_classname(driver, By, time, "login-page-primary-button")

btn_click_classname(driver, By, time, "login-page-primary-button")

btn_click_css_selector(driver, By, time, "button.dashboard-show-bank-statement")

# Parent div /html/body/div[1]/div[1]/div[2]/div/div/div[2]

# Child div /html/body/div[1]/div[1]/div[2]/div/div/div[2]/div[1]

selected_months = driver.find_elements(By.XPATH, '/html/body/div[1]/div[1]/div[2]/div/div/div[2]')
print(selected_months)

f = open("demofile2.txt", "a")

for month in selected_months:
    print(month.text)
    f.write(month.text)

    
#for month in selected_months:
#    btn_click_css_selector(driver, By, time, "button.btn-expand-month btn btn-default")
#    items = driver.find_element(By.CLASS_NAME, "list-items")
#    print(items)

#list-item status-ok clickable

time.sleep(300)

driver.quit()
