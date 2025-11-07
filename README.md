# 🚏 ODsay Multimodal Route Planner · Personalized UI

A **personalized multimodal route planner** for public transportation (subway/bus) in the Seoul metropolitan area.
It uses the **Kakao Local (REST) API** to geocode addresses into coordinates, and the **ODsay API** to fetch route candidates.
By incorporating **congestion data** (Seoul subway/bus) and user preferences (mode weights, walking limits, etc.),
it computes optimized travel routes.
A **Streamlit UI** with a **Folium map** provides an intuitive interface and visualization.

---

## 🧭 Key Features

* **Automatic geocoding** of departure/destination (Kakao REST API)
* **Multimodal route search** via ODsay API
* **Seoul subway/bus congestion data integration**
* **Adjustable preferences** for subway, bus, and walking
* **Configurable walking limit and max congestion threshold**
* **Learning mode**: updates user preferences based on chosen routes
* **Folium map-based visualization**
* **The software operates exclusively in Korea.**
---

⚠️ **Congestion data must be downloaded manually.**
This project relies on open datasets from the **Seoul Metro** and **Seoul Open Data Plaza**.
Please download the CSV files below and place them in the `data/` folder.

* [Seoul Open Data Plaza – Subway Congestion](https://data.seoul.go.kr/dataList/OA-15067/S/1/datasetView.do)
* [Seoul Open Data Plaza – Bus Congestion](https://data.seoul.go.kr/dataList/OA-12914/S/1/datasetView.do)
  (*Choose datasets corresponding to your target area.*)

---

## 🖼️ UI Examples

### ⚙️ Main Execution (Route Selection and Map Display)

![Run Screen](./assets/run.png)

### 🔍 Search Screen

![Search Screen](./assets/search.png)

### 🚍 Bus Preference Example

![Bus Preference](./assets/bus_prefer_search_map.png)

### 🚇 Subway Preference Example

![Subway Preference](./assets/subway_prefer_search_map.png)

---

## 📂 Project Structure

```
├─ planner.py               # Core logic: route planning, congestion computation, map rendering
├─ plannerui.py             # Streamlit-based user interface
├─ requirements.txt         # Dependency list
├─ data/                    # Place congestion CSV files here (manual download required)
│   ├─ subway_congestion.csv
│   └─ bus_congestion.csv
├─ assets/
│   ├─ run.png
│   ├─ search.png
│   ├─ bus_prefer_search_map.png
│   └─ subway_prefer_search_map.png
```

---

## 🔑 API Key Setup

### 🟡 Kakao REST API Key

1. Create an app at [Kakao Developers](https://developers.kakao.com)
2. Copy your **REST API key**
3. Add your **domain/IP** in platform settings
4. Register as an environment variable:

```bash
export KAKAO_REST_KEY="YOUR_KAKAO_REST_API_KEY"
```

---

### 🟡 ODsay API Key

1. Get your key from [ODsay Open API](https://dev.odsay.com)
2. Set the service platform to **Server**
3. Add your **IP address** to the allowlist
4. Use the key in code as **ODSAY_API**
5. Register as an environment variable:

```bash
export ODSAY_API="YOUR_ODSAY_SERVER_API_KEY"

# Optional compatibility variable
export ODSAY_KEY="$ODSAY_API"
```

---

## ⚙️ How to Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run Streamlit:

```bash
streamlit run plannerui.py
```

3. Open your browser and go to:

```
http://localhost:8501
```

---

## 📘 References

* [Kakao Developers](https://developers.kakao.com)
* [ODsay Open API](https://dev.odsay.com)
* [Seoul Open Data Plaza](https://data.seoul.go.kr)
* [Streamlit Official Site](https://streamlit.io)
