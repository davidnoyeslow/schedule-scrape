from flask import Flask, request, send_file, render_template_string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from icalendar import Calendar, Event
from datetime import datetime
import pytz
import tempfile
import time
import os

app = Flask(__name__)

HTML_FORM = """ ... """  # your HTML form here

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        ics_file = generate_ical(email, password)
        return send_file(ics_file, as_attachment=True, download_name="schedule.ics")
    return render_template_string(HTML_FORM)

def generate_ical(email, password):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # --- LOGIN ---
    driver.get("https://innerview.wholefoods.com/")
    time.sleep(3)
    driver.find_element(By.ID, "i0116").send_keys(email + Keys.RETURN)
    time.sleep(2)
    driver.find_element(By.ID, "i0118").send_keys(password + Keys.RETURN)
    time.sleep(3)
    try:
        driver.find_element(By.ID, "idBtn_Back").click()
    except:
        pass

    # --- SCRAPE ---
    driver.get("https://innerview.amazon.dev/schedule")
    time.sleep(5)

    calendar = Calendar()
    calendar.add('prodid', '-//My Work Schedule//mxm.dk//')
    calendar.add('version', '2.0')

    rows = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="row-info"]')

    for row in rows:
        day_elem = row.find_element(By.CSS_SELECTOR, 'p[mdn-text]')
        day_str = day_elem.text.replace("(Today) ", "")
        day_dt = datetime.strptime(day_str, "%A, %b %d")
        day_dt = day_dt.replace(year=datetime.now().year)

        shifts = row.find_elements(By.CSS_SELECTOR, 'div[data-testid="shift-info"]')
        for shift in shifts:
            times = shift.find_elements(By.CSS_SELECTOR, 'p[mdn-text]')
            start_str = times[0].text if len(times) > 0 else ""
            end_str = times[1].text if len(times) > 1 else ""
            start_time = datetime.strptime(start_str, "%I:%M %p")
            end_time = datetime.strptime(end_str, "%I:%M %p")
            start_dt = day_dt.replace(hour=start_time.hour, minute=start_time.minute)
            end_dt = day_dt.replace(hour=end_time.hour, minute=end_time.minute)

            location_elem = row.find_elements(By.CSS_SELECTOR, 'div.css-bp4v2f p')
            location = location_elem[0].text if location_elem else ""

            event = Event()
            event.add('summary', 'Work Shift')
            event.add('dtstart', pytz.timezone("America/New_York").localize(start_dt))
            event.add('dtend', pytz.timezone("America/New_York").localize(end_dt))
            event.add('location', location)
            calendar.add_component(event)

    driver.quit()

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ics")
    with open(tmp_file.name, "wb") as f:
        f.write(calendar.to_ical())

    return tmp_file.name

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
