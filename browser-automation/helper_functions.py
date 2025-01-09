import traceback

def btn_click_classname(driver, By, time, cl_name):
    try:
        login_button = driver.find_element(By.CLASS_NAME, cl_name)
        login_button.click()
        time.sleep(2)
    except Exception:
        print(traceback.format_exc())

def btn_click_css_selector(driver, By, time, selector):
    try:
        time.sleep(2)
        login_button = driver.find_element(By.CSS_SELECTOR, selector)
        login_button.click()
        time.sleep(2)
    except Exception:
        print(traceback.format_exc())
