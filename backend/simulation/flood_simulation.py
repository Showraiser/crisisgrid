"""
Standalone simulation script — run during the demo recording:
    python simulation/flood_simulation.py

Streams 30 pre-written realistic flood reports into Firestore over ~90 seconds.
Scenario: Monsoon flood across Assam, India. Real place names, real coordinates.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import random
from datetime import datetime
from config import db

REPORTS = [
    # ── MEDICAL (8) ───────────────────────────────────────────────────────────
    {"lat": 26.5800, "lng": 93.1700, "place": "Kaziranga, Nagaon",
     "text": "Hospital basement flooded. 30 patients need emergency evacuation. Staff overwhelmed. Water level rising rapidly.", "sev": 10},

    {"lat": 26.5850, "lng": 93.1750, "place": "Bokakhat PHC, Golaghat",
     "text": "Primary health centre cut off by floodwater. 12 injured people stranded inside with no medicines or electricity.", "sev": 9},

    {"lat": 26.9500, "lng": 94.1700, "place": "Majuli Island clinic",
     "text": "Two elderly women with serious injuries after house collapse. No road access. Need medical boat immediately.", "sev": 9},

    {"lat": 26.2500, "lng": 92.3300, "place": "Morigaon district hospital approach",
     "text": "Bridge to district hospital submerged. Pregnant woman in labour, cannot reach hospital. Critical situation.", "sev": 10},

    {"lat": 26.4800, "lng": 90.5600, "place": "Bongaigaon urban area",
     "text": "Snake bites reported in 3 households after flooding pushed snakes into homes. Antivenom urgently needed.", "sev": 7},

    {"lat": 26.0200, "lng": 89.9800, "place": "Dhubri civil hospital road",
     "text": "Ambulance stuck 2 km from hospital. Road completely under water. Patient with chest pain inside vehicle.", "sev": 8},

    {"lat": 26.1700, "lng": 90.6200, "place": "Goalpara riverside",
     "text": "Cholera symptoms reported in 8 people sheltering in school building. Water source contaminated.", "sev": 7},

    {"lat": 26.6300, "lng": 92.7900, "place": "Tezpur medical college area",
     "text": "Power outage at medical college. ICU patients on ventilators at risk. Generator fuel running low.", "sev": 10},

    # ── SHELTER (8) ───────────────────────────────────────────────────────────
    {"lat": 26.5820, "lng": 93.1680, "place": "Kaziranga village cluster",
     "text": "About 200 villagers on rooftops. Houses fully submerged. Been here 14 hours. No food or water.", "sev": 9},

    {"lat": 26.9600, "lng": 94.1800, "place": "Majuli north bank",
     "text": "150 families displaced from low-lying char land. Sheltering under trees. No relief camp nearby. Children shivering.", "sev": 8},

    {"lat": 26.2400, "lng": 92.3200, "place": "Morigaon rural belt",
     "text": "Entire hamlet washed out. 50 people have nothing left. Requesting tent shelters and dry clothes urgently.", "sev": 8},

    {"lat": 26.4750, "lng": 90.5500, "place": "Bongaigaon low zone",
     "text": "School used as shelter is now at risk of collapse. Roof cracked. Need to move 80 people immediately.", "sev": 9},

    {"lat": 26.3400, "lng": 92.6800, "place": "Nagaon char area",
     "text": "60 fishermen families on raised road embankment with no shelter overhead. Heavy rain continuing.", "sev": 6},

    {"lat": 26.3200, "lng": 91.0100, "place": "Barpeta flood plain",
     "text": "River embankment breached at midnight. 400 people evacuated to nearby high school. Overcrowded, no sanitation.", "sev": 7},

    {"lat": 26.0100, "lng": 89.9900, "place": "Dhubri char island",
     "text": "Char residents completely surrounded by floodwater. No boats available locally. Around 120 people trapped.", "sev": 9},

    {"lat": 26.5870, "lng": 93.1720, "place": "Kaziranga forest fringe village",
     "text": "Wildlife displaced by flood entering village. 30 families afraid to come down from rooftops due to animals.", "sev": 5},

    # ── FOOD (7) ─────────────────────────────────────────────────────────────
    {"lat": 26.9550, "lng": 94.1750, "place": "Majuli central",
     "text": "No food supply reached Majuli for 3 days. Ferry service suspended. Market fully flooded. 10,000 people affected.", "sev": 8},

    {"lat": 26.2450, "lng": 92.3250, "place": "Morigaon supply route",
     "text": "NH37 flooded at 3 points cutting off Morigaon. All trucks carrying food supplies stuck. Stock for 2 days only.", "sev": 7},

    {"lat": 26.4800, "lng": 90.5650, "place": "Bongaigaon relief camp",
     "text": "Relief camp running out of dry rations. 300 people here, only food for 100 remaining. Request urgent resupply.", "sev": 8},

    {"lat": 26.3450, "lng": 92.6850, "place": "Nagaon relief distribution point",
     "text": "Distribution point submerged. Stocks of rice and dal destroyed by water. Nothing left to give out.", "sev": 6},

    {"lat": 26.3250, "lng": 91.0050, "place": "Barpeta distribution centre",
     "text": "Only one functional kitchen for 500 displaced people. Running 12 hours behind on meals. Infants not fed.", "sev": 7},

    {"lat": 26.1700, "lng": 90.6150, "place": "Goalpara town",
     "text": "All shops in market area flooded. No way to purchase food locally. People surviving on biscuits.", "sev": 5},

    {"lat": 26.6400, "lng": 92.7950, "place": "Tezpur periphery villages",
     "text": "6 villages beyond flood barrier have had no food supply in 48 hours. Approximately 2000 residents affected.", "sev": 8},

    # ── EVACUATION (7) ────────────────────────────────────────────────────────
    {"lat": 26.5810, "lng": 93.1710, "place": "Kaziranga NH37 stretch",
     "text": "NH37 under 4 feet of water near Kohora. 15 vehicles including a bus stranded. Around 60 people need evacuation.", "sev": 8},

    {"lat": 26.9480, "lng": 94.1680, "place": "Majuli ferry ghat",
     "text": "Ferry ghat destroyed. 300 people queuing for evacuation but no functional boats. Panic building.", "sev": 9},

    {"lat": 26.0150, "lng": 89.9850, "place": "Dhubri riverside colony",
     "text": "Entire riverside colony must evacuate. River expected to breach bank in 2-3 hours per local reports.", "sev": 9},

    {"lat": 26.4820, "lng": 90.5580, "place": "Bongaigaon railway colony",
     "text": "Railway tracks submerged. 200 railway staff families in low-lying quarters need immediate evacuation.", "sev": 7},

    {"lat": 26.2480, "lng": 92.3280, "place": "Morigaon river bank",
     "text": "Elderly and disabled people unable to self-evacuate from 3 riverside villages. Need boats with ramps.", "sev": 8},

    {"lat": 26.1650, "lng": 90.6180, "place": "Goalpara Brahmaputra bank",
     "text": "Embankment crack widening fast. Engineers estimate breach within 6 hours. 500 households in danger zone.", "sev": 9},

    {"lat": 26.3480, "lng": 92.6820, "place": "Nagaon island village",
     "text": "Small island village completely surrounded. 80 residents including 20 children need helicopter or boat evacuation.", "sev": 8},
]


def run():
    col = db.collection("reports")
    total = len(REPORTS)
    print(f"\n🌊 CrisisGrid Flood Simulation — Assam Monsoon Scenario")
    print(f"   Streaming {total} reports over ~90 seconds...\n")

    for i, report in enumerate(REPORTS, start=1):
        jitter = random.uniform(-0.5, 0.5)
        delay  = (90 / total) + jitter

        doc = {
            "lat":       report["lat"] + random.uniform(-0.003, 0.003),
            "lng":       report["lng"] + random.uniform(-0.003, 0.003),
            "text":      report["text"],
            "photoUrl":  None,
            "timestamp": datetime.utcnow(),
            "userId":    "simulation_user",
        }
        col.add(doc)
        print(f"  ✓ Report {i:02d}/{total} — {report['place']} — severity hint: {report['sev']}")

        if i < total:
            time.sleep(max(0.5, delay))

    print(f"\n✅ Simulation complete. {total} reports written to Firestore.")
    print("   Watch the dashboard — heatmap should evolve within seconds.\n")


if __name__ == "__main__":
    run()
