*** Settings ***
Documentation    A simple test to open Google.com in headless Chrome.
Library          SeleniumLibrary    timeout=10s  # Set a default timeout for Selenium commands

*** Variables ***
${TARGET_URL}      https://www.google.com
${BROWSER}         Chrome
${CHROME_DRIVER_PATH}=    ../chromedriver       

*** Test Cases ***
Verify Can Open Google In Headless Chrome
    Log To Console    Starting Chrome test...
    Open Chrome To Google
    Maximize Browser Window
    Wait Until Element Is Visible    xpath=/html/body/div[2]/div[2]/div[3]/span/div/div/div/div[3]/div[1]/button[1]
    Click Element                  xpath=/html/body/div[2]/div[2]/div[3]/span/div/div/div/div[3]/div[1]/button[1]
    Wait Until Element Is Visible   xpath=/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div[1]/div[2]/textarea
    Title Should Be       Google           
    Log To Console    Successfully reached Google.com and verified title.
    

*** Keywords ***
Open Chrome To Google
    # Define Chrome options for headless mode
    # Note: Newer Chrome/ChromeDriver versions might require "--headless=new"
    ${chrome_options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys, selenium.webdriver
    #Call Method    ${chrome_options}    add_argument    --headless
    # Call Method    ${chrome_options}    add_argument    --headless=new  # Use this line instead if the above doesn't work
    Call Method    ${chrome_options}    add_argument    --disable-gpu   # Often recommended for headless
    Call Method    ${chrome_options}    add_argument    --no-sandbox    # May be needed in some environments (like Docker)
    Call Method    ${chrome_options}    add_argument    --disable-dev-shm-usage # May be needed in some environments (like Docker)


    # --- Option 1: chromedriver is in PATH (Recommended) ---
    Open Browser    ${TARGET_URL}    ${BROWSER}    options=${chrome_options}

    # --- Option 2: Specify chromedriver path explicitly ---
    # Comment out the line above and uncomment the line below if using executable_path
    # Open Browser    ${TARGET_URL}    ${BROWSER}    executable_path=${CHROME_DRIVER_PATH}    options=${chrome_options}

    Log    Browser opened in headless mode to ${TARGET_URL}