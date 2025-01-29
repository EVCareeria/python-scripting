from helper_functions import scrape_account_transactions, open_and_close_month, scrape_account_transactions_from_menu
import os
from shutil import move, rmtree

def transactions_data(driver, By, WebDriverWait, EC, time, selected_months, Csv):
    # Remove old images directory
    if os.path.isdir("./images"):
        rmtree("./images")

    with open("demofile2.txt", "a") as f:
        for month in range(len(selected_months)):
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.month-timeline-item.completed.hideEvents')))
            selected_months = driver.find_elements(By.CSS_SELECTOR, 'div.month-timeline-item.completed.hideEvents')
            print(f"Count of months: {len(selected_months)}")
            print(f"Current month: : {month}")
            time.sleep(2)

            try:

                month_element = selected_months[month]
                month_name = selected_months[month].text
                print(f"month_element : {month_element}")
                print(f"month_element value: {month_name}")
                month_button = month_element.find_element(By.CSS_SELECTOR, 'button.btn-expand-month.btn')

                # Create base template csv with headers
                csv = Csv(month_name)
                csv.create_csv()

                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(month_button))
                # Perform the click
                month_button.click()

                try:
                    index = month + 1
                    WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="main"]/div/div[2]/div[{index}]/div/div/div/div[3]')))
                    clickable_sales = month_element.find_elements(By.CSS_SELECTOR, 'div.list-item.status-ok.clickable')
                    non_clickable_sales = month_element.find_elements(By.CSS_SELECTOR,
                                                                      'div.list-item.status-ok.disabled')
                    # list-item status-ok disabled
                    print(f"Count of items clickable_sales: {len(clickable_sales)}")
                    print(f"Count of items non_clickable_sales: {len(non_clickable_sales)}")
                    # Clickable elements
                    for sale in range(len(clickable_sales)):
                        try:
                            print(f"index: {index}")
                            print(f"Current_sale: {sale}")
                            current_sales = driver.find_elements(By.CSS_SELECTOR, 'div.list-item.status-ok.clickable')
                            WebDriverWait(driver, 5).until(EC.element_to_be_clickable(current_sales[sale]))
                            print(f"Text value: {current_sales[sale].text}")
                            current_sales[sale].click()
                            scrape_account_transactions(driver, By, csv)  # Reads the table data and downloads file if available
                            time.sleep(4)
                            driver.back()
                        except Exception as e:
                            print(f"Something went wrong here with: {sale} Error: {e}")
                            time.sleep(30)
                    # Non clickable elements
                    for sale in range(len(non_clickable_sales)):
                        try:
                            print(f"index: {index}")
                            print(f"Current_sale: {sale}")
                            WebDriverWait(driver, 3)
                            current_sales = driver.find_elements(By.CSS_SELECTOR, 'div.list-item.status-ok.disabled')
                            print(f"Text value: {current_sales[sale].text}")
                            element = current_sales[sale]
                            div_above = element.find_element(By.XPATH, "preceding::div[@class='date-row'][1]")
                            date = div_above.text
                            print(f"DIV ABOVE: {div_above.text}")
                            scrape_account_transactions_from_menu(driver, By, csv, element, date)
                            time.sleep(4)
                        except Exception as e:
                            print(f"Something went wrong here with: {sale} Error: {e}")
                            time.sleep(30)
                    print(f"FINISHED MONTH: {month_name}")
                except Exception as e:
                    print(f"Failed to click items: {e}")

                time.sleep(2)
                # Create directory for corresponding month
                if not os.path.exists(f"./images/{month_name}"):
                    os.makedirs(f"./images/{month_name}")

                # Move only files to that corresponding months directory
                for f in os.listdir("./images"):
                    full_path = os.path.join("./images", f)
                    if os.path.isfile(full_path):
                        move(full_path, os.path.join(f"./images/{month_name}", f))


                open_and_close_month(driver, By, WebDriverWait, EC,
                                     'div.month-timeline-item.completed:not(.hideEvents)')
                driver.refresh()
                driver.getTitle()
                time.sleep(2)
            except Exception as e:
                print(f"Failed to click on element: {e}")

