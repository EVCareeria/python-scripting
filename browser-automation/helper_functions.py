import traceback
import re
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
        label_data = []
        elements = driver.find_elements(By.CSS_SELECTOR, 'div.row')

        for element in elements:
            transaction_label = element.find_element(By.CSS_SELECTOR, 'label.cell').text
            transaction_data = element.find_element(By.CSS_SELECTOR, 'div.cell.value, div.expense-type-text, div.cell.vertical-top.textarea-container').text
            if transaction_data and len(transaction_data) < 1:
                transaction_data = ''
            if len(label_data) == 0 and transaction_label == "Nimi":
                try:
                    transaction_data = element.find_element(By.XPATH, '//*[@id="main"]/div/div/div[2]/div[1]/div[2]/div/p').text
                    transaction_data = transaction_data.split(",")[0]
                    transaction_data = transaction_data.split("(")[1]
                except Exception:
                    print("No name element found")
            if transaction_label == "Viitenumero":
                transaction_label = "Viite"
            if "Viesti" in label_data and transaction_label == "Viesti":
                transaction_label = "LisätiedotViesti"
            if len(label_data) == 1 and transaction_label != "Viite":
                label_data.append("Viite")
                data.append(str(""))

            label_data.append(transaction_label)
            data.append(str(transaction_data))
            print(transaction_label)
            print(transaction_data)
        print(f"Label data: {label_data}")
        data = check_data(data, label_data)
        print(f"Current data: {data}")
        csv_module.add_data(data)
        try:
            button = driver.find_element(By.XPATH, '//button[@data-balloon="Lataa"]')
            button.click()
        except NoSuchElementException:
            print("Button not found")
    except Exception:
        print(traceback.format_exc())

# Makes sure that data is stored under correct headers in csv
def check_data(data, label_data):
    custom_order = ["Nimi", "Viite", "Maksupäivä", "Arvopäivä", "Summa", "Viesti", "Kulutyyppi", "LisätiedotViesti"]    # Specify labels

    missing_labels = [label for label in custom_order if label not in label_data]   # If some of the labels are missing, add them to end of the list
    label_data.extend(missing_labels)
    data.extend([''] * len(missing_labels))     # Match the count of newly added labels with empty strings

    sorted_labels = sorted(label_data, key=lambda label: custom_order.index(label) if label in custom_order else str(''))
    sorted_data = [data[label_data.index(label)] if label in label_data else "" for label in sorted_labels]

    return sorted_data



def scrape_account_transactions_from_menu(driver, By, csv_module, element, date):
    try:
        data = []
        name = element.find_element(By.CSS_SELECTOR, 'div.name')
        message = element.find_element(By.CSS_SELECTOR, 'div.message')
        total = element.find_element(By.CSS_SELECTOR, 'div.sum')
        data.append(str(name.text))
        data.append(str(""))
        data.append(str(date))
        data.append(str(date))
        data.append(str(total.text))
        data.append(str(message.text))
        print(f"Data in non clickable element: {data}")
        csv_module.add_data(data)

    except Exception:
        print(traceback.format_exc())

def open_and_close_month(driver, By, WebDriverWait, EC, selector):
    selected_month = driver.find_element(By.CSS_SELECTOR, selector)
    month_button = selected_month.find_element(By.CSS_SELECTOR, 'button.btn-expand-month.btn')
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(month_button))
    # Perform the click
    month_button.click()