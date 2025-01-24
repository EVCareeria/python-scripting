import traceback
from selenium.common.exceptions import NoSuchElementException


def btn_click_classname(driver, By, time, cl_name):
    try:
        button = driver.find_element(By.CLASS_NAME, cl_name)
        button.click()
        time.sleep(2)
    except Exception:
        print(traceback.format_exc())

def btn_click_css_selector(driver, By, time, selector):
    try:
        time.sleep(2)
        button = driver.find_element(By.CSS_SELECTOR, selector)
        button.click()
        time.sleep(2)
    except Exception:
        print(traceback.format_exc())

def btn_click_xpath_selector(driver, By, time, selector):
    try:
        time.sleep(2)
        button = driver.find_element(By.XPATH, selector)
        button.click()
        time.sleep(2)
    except Exception:
        print(traceback.format_exc())

def scrape_account_transactions(driver, By, csv_module):
    try:
        data = []
        for i in range(1, 6):
            element = f'//*[@id="main"]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div[{i}]'
            transaction_label = driver.find_element(By.XPATH, f'{element}/label')
            transaction_data = driver.find_element(By.XPATH, f'{element}/div')
            data.append(str(transaction_data.text))
            print(transaction_label.text)
            print(transaction_data.text)
        print("Current data: ", data)
        csv_module.add_data(data)
        try:
            button = driver.find_element(By.XPATH, '//button[@data-balloon="Lataa"]')
            button.click()
        except NoSuchElementException:
            print("Button not found")
    except Exception:
        print(traceback.format_exc())
