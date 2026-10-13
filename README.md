# Tablet Counter (prototype)

A self-hosted tablet counting web application. An analyst uses a phone browser to upload an existing photograph and enter case/item/analyst fields. The **computer** processes the image using Python and OpenCV and returns a numbered, annotated image and an object count. The phone is the client, not the processor. No cloud service or internet connection is needed during normal operation.

> **Prototype only:** Not validated for forensic or evidentiary use. Manually verify every numbered outline and the count. Do **not** use actual evidence photographs or identifying case information without organizational approval, including review of security and data handling.

## Requirements

- Ubuntu computer (previous test environment: Ubuntu 24.04, Python 3.12); Python 3.10+ is recommended.
- Internet connection **for initial installation** of system packages and Python dependencies.
- Phone with a browser and an existing photograph in its photo library.
- Optional: Wi-Fi adapter and driver supporting access-point (hotspot) mode for a stand-alone wireless connection. Otherwise, use the same trusted LAN for the phone and computer.

## First-time setup on Ubuntu

In Terminal:

```bash
sudo apt update
sudo apt install python3-venv python3-pip git
git clone https://github.com/github-aim/pill-counter.git
cd pill-counter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

If virtual-environment creation fails with an `ensurepip` error, install the matching package (Ubuntu 24.04: `sudo apt install python3.12-venv`) and repeat `python3 -m venv .venv`. No full operating-system upgrade is necessary.

The application should start listening on port **5000**. Keep the terminal running. Test on the computer with **http://127.0.0.1:5000**. Stop with **Ctrl+C**.

### Using the phone on a shared trusted network

Connect both devices to the same trusted network. Find the computer's LAN IPv4 address with `ip -4 addr`. In the phone browser visit `http://<COMPUTER-IP>:5000`. Ensure local firewall settings allow the connection. **Do not forward port 5000 to the public internet.**

## Stand-alone Wi-Fi hotspot (Ubuntu NetworkManager)

A hotspot lets the computer and phone communicate without an external router or internet. Not all Wi-Fi adapters support hotspot mode. Install dependencies **before** turning on the hotspot if the same adapter provides internet access.

Identify the Wi-Fi interface (for example `wlp3s0`) and check its capabilities:

```bash
nmcli device status
nmcli -f WIFI-PROPERTIES.AP device show
```

Look for `WIFI-PROPERTIES.AP: yes`.

Create the hotspot **once**, substituting your interface name and choosing your own strong password (8 characters minimum):

```bash
sudo nmcli device wifi hotspot ifname wlp3s0 con-name TabletCounter ssid TabletCounter password 'CHOOSE-A-STRONG-PASSWORD'
sudo nmcli connection modify TabletCounter 802-11-wireless.band bg 802-11-wireless.channel 6
sudo nmcli connection down TabletCounter
sudo nmcli connection up TabletCounter
```

Check its address:

```bash
ip -4 addr show wlp3s0
```

The earlier ThinkPad assigned `10.42.0.1`, but your computer may have another IP address.

Connect the phone to Wi-Fi network **TabletCounter** using the password you chose. If the phone warns that the network has no internet, choose **stay connected**; some phones otherwise switch to mobile data. Open `http://<HOTSPOT-IP>:5000` in its browser (for example `http://10.42.0.1:5000`). Use **http**, not https.

To reconnect the saved hotspot after restarting the computer:

```bash
sudo nmcli connection up TabletCounter
```

## Operating the tablet counter

1. Lay tablets on a clean, uniform surface with a contrasting background. Separate them so none are touching.
2. Use diffuse, even lighting with minimal shadows and glare. Take a focused, approximately overhead photograph with the phone's camera app.
3. Open the application URL in the phone browser.
4. Enter case number, item number, and analyst identifier (**fictitious information for demonstrations**).
5. Choose **Automatic**, or specify **light tablets on dark background** / **dark tablets on light background**.
6. Select the existing image from the phone's photo library and press **Count tablets**.
7. Inspect the output image. **Each accepted object is outlined in green and assigned a yellow number.** Verify none were missed or counted twice.
8. Use **Save annotated photograph** to save the result or **Count another image** to start again.

### Where data goes

The computer processes the uploaded photograph locally in memory. The current code does not separately save the original photo, but it saves the annotated JPEG under `results/` and appends a row to `results/counts.csv` with date/time, case, item, analyst, count, selection, and output filename. `results/` is excluded from Git by `.gitignore`. Local results still require appropriate retention and security practices.

## How the algorithm works

OpenCV resizes photographs exceeding 1600 pixels on their longest side; converts to grayscale; applies a Gaussian blur; and uses **Otsu thresholding** to divide lighter from darker image regions. It evaluates bright and dark object masks (or uses the analyst's selected polarity). It performs morphological opening to reduce tiny features, extracts external contours, rejects contours based on relative area, size, or image-edge contact, then counts and numbers those remaining.

**This is traditional computer vision, not trained artificial intelligence or chemical identification.** Every accepted contour is considered one object. Touching tablets can merge into one region. Shadows, reflections, debris, printed markings, out-of-focus edges, or poor contrast can cause misses or duplicate detections. An object of similar size and contrast that is not a tablet may be counted.

## Troubleshooting

- **`ModuleNotFoundError`:** activate `.venv` and run `python -m pip install -r requirements.txt`.
- **Virtual environment fails / `ensurepip`:** install the correct `python3.x-venv` package and recreate `.venv`.
- **Phone cannot see TabletCounter Wi-Fi:** verify `nmcli connection show --active`, confirm AP support, and try the 2.4 GHz/channel 6 settings above.
- **Phone connected, page not loading:** confirm `python app.py` is still running, use `http://` and port `5000`, check the computer IP/firewall, and test localhost on the computer first. A phone's VPN or mobile-data switching can also interfere.
- **Incorrect count:** retake the photo; improve contrast, lighting, focus, and separation; use the manual light/dark setting; verify all labels.
- **Cannot select an image:** this version expects an **existing photo** in the phone library; take the picture first with the regular camera app.
- **Port 5000 in use:** stop the previous app instance before starting another.

## Restart checklist

```bash
# Only if using the saved hotspot:
sudo nmcli connection up TabletCounter

cd ~/pill-counter  # or the directory containing this repository
source .venv/bin/activate
python app.py
```

On the phone, connect to the hotspot and visit `http://<COMPUTER-IP>:5000`. Keep the terminal open.

## Security and status

This demo listens on `0.0.0.0:5000` using the Flask development server and ordinary **HTTP**, without login/authentication or HTTPS. Anyone able to access the server's network port can use its interface, and output images can be viewed using their URLs. Run only on a controlled network. Do not make it publicly accessible or use real evidentiary materials without security review and laboratory authorization.

The application is the **last reconstructed code package shared for this project**, not a byte-for-byte export from the unavailable original ThinkPad. It is custom Python code built on Flask, NumPy and OpenCV, **not copied from another published pill-counting project**. Earlier demonstration tests reportedly returned correct counts of 26 and 97 separated tablets under selected conditions, but **these do not establish a validated accuracy rate**. Re-test this repository build on the new computer.

## Files

- `app.py` — server, HTML interface, counting algorithm, annotated result and logging.
- `requirements.txt` — Python dependencies.
- `.gitignore` — prevents committing local results, virtual environments and temporary files.
- `LICENSE` — MIT license for this repository's custom code; third-party dependencies keep their own licenses.
