from helper_functions import btn_click_xpath_selector
from shutil import move
import os
def get_documents(driver, By, time, WebDriverWait, EC):
    btn_click_xpath_selector(driver, By, time, '//*[@id="app"]/div[1]/div/nav/ul/li[8]/a')
    btn_click_xpath_selector(driver, By, time, '//*[@id="app"]/div[1]/div/nav/ul/li[8]/ul/li[3]/a')
    documents = driver.find_elements(By.CSS_SELECTOR, 'a.list-item.clickable.item-container')
    disabled = driver.find_elements(By.CSS_SELECTOR, 'a.list-item.clickable.item-container.isDisabled')
    print(f"Count of disabled elements: {len(disabled)}")
    correct_url = driver.current_url
    # Clickable elements
    for index in range(len(documents)):
        try:
            time.sleep(1)
            if driver.current_url != correct_url:
                driver.back()
                driver.refresh()
            print(f"Current_index: {index}")
            documents = driver.find_elements(By.CSS_SELECTOR, 'a.list-item.clickable.item-container')
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable(documents[index]))
            date =  documents[index].find_element(By.CSS_SELECTOR, 'div.document-date').text
            date = date.split('.')[2]
            documents[index].click()
            time.sleep(1)
            try:
                create_dir_and_move_files(date)
            except Exception as e:
                print(f"Could not create or move files: {e}")


        except Exception as e:
            print("Could not click document")



# Makes the check with each file addition, horrible for performance, but works
# Add documents to corresponding directory with correct year
def create_dir_and_move_files(date):
    if not os.path.exists(f"./images/documents/{date}"):
        os.mkdir(f"./images/documents/{date}")

    for f in os.listdir("./images"):
        full_path = os.path.join("./images", f)
        if os.path.isfile(full_path):
            move(full_path, os.path.join(f"./images/documents/{date}", f))