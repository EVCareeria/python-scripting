from helper_functions import btn_click_xpath_selector
import os
from shutil import move
def get_reports(driver, By, time, WebDriverWait, EC):
    btn_click_xpath_selector(driver, By, time, '//*[@id="app"]/div[1]/div/nav/ul/li[8]/a')
    btn_click_xpath_selector(driver, By, time, '//*[@id="app"]/div[1]/div/nav/ul/li[8]/ul/li[4]/a')

    for index in range(70):
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button.MuiButtonBase-root.MuiIconButton-root.MuiIconButton-sizeMedium.css-1x6hzgh')))
            month_name = driver.find_element(By.CSS_SELECTOR, 'h2.MuiTypography-root.MuiTypography-h2.css-1eumwv7').text

            buttons = driver.find_elements(By.CSS_SELECTOR,
                                           'button.MuiButtonBase-root.MuiButton-root.MuiButton-contained.MuiButton-containedPrimary.MuiButton-sizeMedium.MuiButton-containedSizeMedium.MuiButton-colorPrimary.MuiButton-root.MuiButton-contained.MuiButton-containedPrimary.MuiButton-sizeMedium.MuiButton-containedSizeMedium.MuiButton-colorPrimary.css-zte6e0')
            print(f"Count of download buttons: {len(buttons)}")
            for button in buttons:
                try:
                    button.click()
                except Exception:
                    print(f"Could not click the button: {button}")
            time.sleep(1)
            # Create directory for corresponding month
            if not os.path.exists(f"./reports/{month_name}"):
                os.makedirs(f"./reports/{month_name}")

                # Move only files to that corresponding months directory
            for f in os.listdir("./images"):
                full_path = os.path.join("./images", f)
                if os.path.isfile(full_path):
                    move(full_path, os.path.join(f"./reports/{month_name}", f))
            time.sleep(1)
            button = driver.find_element(By.CSS_SELECTOR,
                                         'button.MuiButtonBase-root.MuiIconButton-root.MuiIconButton-sizeMedium.css-1x6hzgh')
            time.sleep(1)
            button.click()

        except Exception as e:
            print(f"Error encountered: {e}")