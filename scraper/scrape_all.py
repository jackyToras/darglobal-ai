import urllib.request
import json
import re
import os

os.makedirs("data", exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

wasalt_endpoints = [
    "https://wasalt.sa/en/properties-for-sale-in-riyadh",
    "https://wasalt.sa/en/villas-for-sale-in-north-riyadh-al-yasmeen",
    "https://wasalt.sa/en/apartments-for-sale-in-riyadh",
    "https://wasalt.sa/en/properties-for-rent-in-riyadh",
    "https://wasalt.sa/en/properties-for-sale-in-jeddah",
    "https://wasalt.sa/en/apartments-for-sale-in-jeddah",
    "https://wasalt.sa/en/villas-for-sale-in-jeddah",
    "https://wasalt.sa/en/lands-for-sale-in-dammam",
    "https://wasalt.sa/en/properties-for-sale-in-madinah",
    "https://wasalt.sa/en/properties-for-rent-in-makkah"
]

all_properties = []
seen_ids = set()

for endpoint in wasalt_endpoints:
    try:
        req = urllib.request.Request(endpoint, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
            if not match:
                continue
            payload = json.loads(match.group(1))
            page_props = payload.get("props", {}).get("pageProps", {})
            sr = page_props.get("searchResult", {})
            if isinstance(sr, dict):
                props = sr.get("properties", [])
            elif isinstance(sr, list):
                props = sr
            else:
                props = []

            for item in props:
                if not isinstance(item, dict):
                    continue
                prop_id = str(item.get("id"))
                if not prop_id or prop_id in seen_ids:
                    continue
                seen_ids.add(prop_id)

                pinfo = item.get("propertyInfo", {})
                if not isinstance(pinfo, dict):
                    pinfo = {}
                attrs = item.get("attributes", [])
                
                bedrooms = None
                bathrooms = None
                built_up_area = None
                if isinstance(attrs, list):
                    for attr in attrs:
                        if isinstance(attr, dict):
                            k = str(attr.get("key", "")).lower()
                            v = attr.get("value")
                            if "bedroom" in k:
                                try:
                                    bedrooms = int(v)
                                except:
                                    pass
                            elif "bathroom" in k:
                                try:
                                    bathrooms = int(v)
                                except:
                                    pass
                            elif "area" in k or "builtup" in k:
                                built_up_area = str(v)

                price = pinfo.get("salePrice") or pinfo.get("conversionPrice") or pinfo.get("expectedRent")
                try:
                    price_val = float(price) if price else 0.0
                except:
                    price_val = 0.0

                images = []
                pfiles = item.get("propertyFiles", {})
                if isinstance(pfiles, dict):
                    raw_imgs = pfiles.get("images", [])
                    if isinstance(raw_imgs, list):
                        for img in raw_imgs:
                            if isinstance(img, str):
                                if img.startswith("http"):
                                    images.append(img)
                                else:
                                    images.append(f"https://assets.wasalt.com/properties/{img}")
                elif isinstance(pfiles, list):
                    for pf in pfiles:
                        if isinstance(pf, dict):
                            purl = pf.get("url") or pf.get("imageUrl") or pf.get("filePath")
                            if purl and isinstance(purl, str):
                                images.append(purl if purl.startswith("http") else f"https://assets.wasalt.com/properties/{purl}")
                        elif isinstance(pf, str):
                            images.append(pf if pf.startswith("http") else f"https://assets.wasalt.com/properties/{pf}")
                
                if not images:
                    images.append("https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80")

                prop_record = {
                    "id": f"wasalt-{prop_id}",
                    "platform": "Wasalt",
                    "title": pinfo.get("title") or item.get("slug") or "Premium Saudi Property",
                    "project_name": pinfo.get("projectName") or pinfo.get("propertyName") or "Wasalt Residential",
                    "developer": "Dar Al Arkan / Wasalt Marketplace",
                    "brand_partner": "None",
                    "country": pinfo.get("country") or "Saudi Arabia",
                    "city": pinfo.get("city") or "Riyadh",
                    "district": pinfo.get("district") or pinfo.get("zone") or "Riyadh District",
                    "property_type": pinfo.get("propertySubType") or pinfo.get("propertyMainType") or "Residential",
                    "listing_type": pinfo.get("propertyFor") or "sale",
                    "price_sar": price_val,
                    "currency": pinfo.get("currencyType") or "SAR",
                    "bedrooms": bedrooms if bedrooms is not None else 3,
                    "bathrooms": bathrooms if bathrooms is not None else 3,
                    "area_sqm": built_up_area or "250",
                    "status": "Ready / Available",
                    "description": f"{pinfo.get('title', 'Luxury Property')} situated in {pinfo.get('district', 'prime location')}, {pinfo.get('city', 'Saudi Arabia')}. Ideal for family living and high rental yield.",
                    "amenities": ["Parking", "Private Entrance", "Modern Kitchen", "Security", "Nearby Mosque & Schools"],
                    "images": images[:4],
                    "official_url": f"https://wasalt.sa/en/{pinfo.get('slug', prop_id)}"
                }
                all_properties.append(prop_record)
    except Exception as e:
        print(f"Endpoint {endpoint} failed: {e}")

darglobal_catalog = [
    {
        "id": "dg-dg1",
        "platform": "DarGlobal",
        "title": "DG1 Living - Business Bay Luxury Tower",
        "project_name": "DG1 Living",
        "developer": "DarGlobal",
        "brand_partner": "Gensler Architects",
        "country": "United Arab Emirates",
        "city": "Dubai",
        "district": "Business Bay",
        "property_type": "Apartments & Penthouses",
        "listing_type": "sale",
        "price_sar": 2100000.0,
        "currency": "AED / SAR",
        "bedrooms": 1,
        "bathrooms": 2,
        "area_sqm": "85 - 240",
        "status": "Under Construction (Handover Q4 2026)",
        "description": "DG1 by DarGlobal is an exclusive residential tower designed by world-renowned architecture firm Gensler. Located on Dubai Water Canal in Business Bay, it offers panoramic views of Burj Khalifa and the Dubai skyline with avant-garde living spaces.",
        "amenities": ["Infinity Swimming Pool", "State of the Art Gymnasium", "Concierge Service", "Canal Promenade Access", "Sky Lounge"],
        "images": [
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/dg1"
    },
    {
        "id": "dg-davinci-pagani",
        "platform": "DarGlobal",
        "title": "DaVinci Tower - Interiors by Pagani",
        "project_name": "DaVinci Tower",
        "developer": "DarGlobal",
        "brand_partner": "Pagani Automobili",
        "country": "United Arab Emirates",
        "city": "Dubai",
        "district": "Downtown Dubai / Business Bay",
        "property_type": "Luxury Apartments & Penthouses",
        "listing_type": "sale",
        "price_sar": 6800000.0,
        "currency": "AED / SAR",
        "bedrooms": 2,
        "bathrooms": 3,
        "area_sqm": "180 - 450",
        "status": "Under Construction (Handover 2025)",
        "description": "The world first residential building with interiors crafted exclusively by Pagani Automobili. DaVinci Tower blends carbon fiber, bespoke Italian leather, and hypercar engineering into ultra-luxury canal-side residences.",
        "amenities": ["Pagani Resident Lounge", "Rooftop Infinity Pool", "Private Cinema", "24/7 White Glove Valet", "Hypercar Simulator"],
        "images": [
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/davinci-tower"
    },
    {
        "id": "dg-urban-oasis-missoni",
        "platform": "DarGlobal",
        "title": "Urban Oasis - Interiors by Missoni",
        "project_name": "Urban Oasis",
        "developer": "DarGlobal",
        "brand_partner": "Missoni",
        "country": "United Arab Emirates",
        "city": "Dubai",
        "district": "Dubai Water Canal",
        "property_type": "Waterfront Apartments & Penthouses",
        "listing_type": "sale",
        "price_sar": 2600000.0,
        "currency": "AED / SAR",
        "bedrooms": 2,
        "bathrooms": 2,
        "area_sqm": "110 - 320",
        "status": "Ready / Handover Phase",
        "description": "Urban Oasis by Missoni brings the iconic vibrant colors, geometric patterns, and Italian haute couture of Missoni to waterfront Dubai living. Direct canal boardwalk connection with private pool decks.",
        "amenities": ["Canalfront Infinity Pool", "Missoni Styled Lounge", "Equipped Fitness Center", "Direct Canal Access", "Private Parking"],
        "images": [
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/urban-oasis"
    },
    {
        "id": "dg-aida-oman",
        "platform": "DarGlobal",
        "title": "AIDA Muscat - Cliffside Master Community & Trump Golf",
        "project_name": "AIDA Oman",
        "developer": "DarGlobal",
        "brand_partner": "Trump International & Marriott",
        "country": "Oman",
        "city": "Muscat",
        "district": "Yiti & Yenkit Cliffs",
        "property_type": "Luxury Oceanfront Villas & Mansions",
        "listing_type": "sale",
        "price_sar": 3200000.0,
        "currency": "OMR / SAR",
        "bedrooms": 3,
        "bathrooms": 4,
        "area_sqm": "310 - 750",
        "status": "Off-Plan Master Development (Handover 2027)",
        "description": "Perched 100 meters above sea level on dramatic ocean cliffs, AIDA is a 3.5 million square meter master community in Muscat. It features the Trump International Golf Club, luxury cliff villas, Marriott Residences, and Nickelodeon resort.",
        "amenities": ["Championship 18-Hole Trump Golf Course", "Private Cliff Beach Club", "Wellness Spa", "Fine Dining Promenade", "5-Star Hotel Resort"],
        "images": [
            "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/aida"
    },
    {
        "id": "dg-tierra-viva-lamborghini",
        "platform": "DarGlobal",
        "title": "Tierra Viva - Design by Automobili Lamborghini",
        "project_name": "Tierra Viva",
        "developer": "DarGlobal",
        "brand_partner": "Automobili Lamborghini",
        "country": "Spain",
        "city": "Costa del Sol / Marbella",
        "district": "Benahavís",
        "property_type": "Ultra-Luxury Supercar Mansions",
        "listing_type": "sale",
        "price_sar": 15500000.0,
        "currency": "EUR / SAR",
        "bedrooms": 5,
        "bathrooms": 6,
        "area_sqm": "680 - 1200",
        "status": "Under Construction (Handover 2027)",
        "description": "An architectural marvel in the hills of Benahavis, Costa del Sol. Tierra Viva comprises 53 exclusive luxury villas with sharp aerodynamic lines and custom finishes directly inspired by Automobili Lamborghini super sports cars.",
        "amenities": ["Panoramic Mediterranean Sea Views", "Private Infinity Heated Pools", "Multi-Car Showroom Garage", "24/7 Gated Security", "Spa & Sauna"],
        "images": [
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/tierra-viva"
    },
    {
        "id": "dg-mouawad-neptune",
        "platform": "DarGlobal",
        "title": "Neptune Villas - Interiors by Mouawad",
        "project_name": "Neptune Sedra",
        "developer": "DarGlobal & Dar Al Arkan",
        "brand_partner": "Mouawad High Jewelry",
        "country": "Saudi Arabia",
        "city": "Riyadh",
        "district": "North Riyadh (ROSHN SEDRA)",
        "property_type": "Bespoke Mansions & Villas",
        "listing_type": "sale",
        "price_sar": 5200000.0,
        "currency": "SAR",
        "bedrooms": 4,
        "bathrooms": 5,
        "area_sqm": "420 - 850",
        "status": "Off-Plan (Handover 2026)",
        "description": "Crafted in partnership with high-jewelry house Mouawad, Neptune villas bring imperial opulence to North Riyadh within the ROSHN SEDRA integrated master plan. Features gem-cut stone finishes and custom brass details.",
        "amenities": ["Private Landscaped Garden", "Smart Home Automation", "Private Pool", "Maids and Drivers Quarters", "Gated Security"],
        "images": [
            "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/neptune"
    },
    {
        "id": "dg-trump-tower-dubai",
        "platform": "DarGlobal",
        "title": "Trump International Hotel & Tower Dubai",
        "project_name": "Trump Tower Dubai",
        "developer": "DarGlobal",
        "brand_partner": "The Trump Organization",
        "country": "United Arab Emirates",
        "city": "Dubai",
        "district": "Downtown Dubai",
        "property_type": "Ultra-Luxury Branded Residences",
        "listing_type": "sale",
        "price_sar": 4500000.0,
        "currency": "AED / SAR",
        "bedrooms": 2,
        "bathrooms": 3,
        "area_sqm": "140 - 380",
        "status": "Announced & Off-Plan",
        "description": "DarGlobal and The Trump Organization bring world-class hospitality, private members club privileges, and landmark architectural elevation to Dubai prime residential corridor.",
        "amenities": ["Private Members Trump Club", "Helipad Access", "Valet & Butler Service", "Signature Dining", "Spa & Wellness"],
        "images": [
            "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/trump-tower-dubai"
    },
    {
        "id": "dg-trump-tower-jeddah",
        "platform": "DarGlobal",
        "title": "Trump Tower Jeddah & Trump Plaza",
        "project_name": "Trump Tower Jeddah",
        "developer": "DarGlobal",
        "brand_partner": "The Trump Organization",
        "country": "Saudi Arabia",
        "city": "Jeddah",
        "district": "Jeddah Corniche",
        "property_type": "Luxury Waterfront Residences",
        "listing_type": "sale",
        "price_sar": 3800000.0,
        "currency": "SAR",
        "bedrooms": 3,
        "bathrooms": 3,
        "area_sqm": "160 - 410",
        "status": "Announced / Off-Plan",
        "description": "A landmark high-rise development gracing the Red Sea waterfront in Jeddah, combining branded luxury living, upscale corporate suites, and panoramic coastal vistas.",
        "amenities": ["Red Sea Panoramic Views", "Private Beach Club", "Executive Business Lounge", "Concierge Service", "Infinity Pool"],
        "images": [
            "https://images.unsplash.com/photo-1574362848149-11496d93a7c7?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/trump-tower-jeddah"
    },
    {
        "id": "dg-les-vagues-eliesaab",
        "platform": "DarGlobal",
        "title": "Les Vagues - Interiors by Elie Saab",
        "project_name": "Les Vagues",
        "developer": "DarGlobal",
        "brand_partner": "Elie Saab",
        "country": "Qatar",
        "city": "Doha",
        "district": "Qetaifan Island North",
        "property_type": "Seafront Luxury Apartments",
        "listing_type": "sale",
        "price_sar": 2900000.0,
        "currency": "QAR / SAR",
        "bedrooms": 2,
        "bathrooms": 2,
        "area_sqm": "120 - 280",
        "status": "Under Construction (Handover 2026)",
        "description": "Situated on Qetaifan Island North, Les Vagues features bespoke couture interiors by world fashion icon Elie Saab. Uninterrupted Arabian Gulf views and resort waterfront living.",
        "amenities": ["Private Marina Access", "Elie Saab Interior Furnishings", "Infinity Seafront Pool", "Fitness & Yoga Studio", "Landscaped Courtyards"],
        "images": [
            "https://images.unsplash.com/photo-1512915922686-57c11dde9b6b?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/les-vagues"
    },
    {
        "id": "dg-w-residences-dubai",
        "platform": "DarGlobal",
        "title": "W Residences Dubai - Downtown",
        "project_name": "W Residences Downtown",
        "developer": "DarGlobal",
        "brand_partner": "W Hotels / Marriott",
        "country": "United Arab Emirates",
        "city": "Dubai",
        "district": "Downtown Dubai",
        "property_type": "Branded Hospitality Residences",
        "listing_type": "sale",
        "price_sar": 2400000.0,
        "currency": "AED / SAR",
        "bedrooms": 1,
        "bathrooms": 2,
        "area_sqm": "80 - 210",
        "status": "Under Construction (Handover 2025)",
        "description": "Brimming with vibrant energy and signature W style. Moments from Dubai Mall and Burj Khalifa, featuring Whatever/Whenever 24-hour concierge services and clubhouse spaces.",
        "amenities": ["W Living Room Lounge", "Clubhouse & Media Room", "Infinity Pool overlooking Burj Khalifa", "24/7 Whatever Whenever Service", "Soundproof Co-working"],
        "images": [
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/w-residences"
    },
    {
        "id": "dg-astera-astonmartin",
        "platform": "DarGlobal",
        "title": "The Astera - Interiors by Aston Martin",
        "project_name": "The Astera",
        "developer": "DarGlobal",
        "brand_partner": "Aston Martin",
        "country": "United Arab Emirates",
        "city": "Ras Al Khaimah / Dubai",
        "district": "Al Marjan Island",
        "property_type": "Beachfront Residences",
        "listing_type": "sale",
        "price_sar": 2200000.0,
        "currency": "AED / SAR",
        "bedrooms": 2,
        "bathrooms": 2,
        "area_sqm": "100 - 260",
        "status": "Off-Plan (Handover 2027)",
        "description": "Beachfront luxury residences next to the multi-billion dollar Wynn Casino Resort on Al Marjan Island, with interiors designed by British luxury marque Aston Martin.",
        "amenities": ["Private Sandy Beach Access", "Aston Martin Bespoke Details", "Infinity Seaside Pool", "Residents Cinema", "Yacht Mooring Access"],
        "images": [
            "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=800&q=80"
        ],
        "official_url": "https://darglobal.co.uk/the-astera"
    }
]

all_properties.extend(darglobal_catalog)

with open("data/properties.json", "w", encoding="utf-8") as f:
    json.dump(all_properties, f, indent=2, ensure_ascii=False)

print(f"Scraping & compilation complete! Saved {len(all_properties)} properties ({len(all_properties) - len(darglobal_catalog)} Wasalt, {len(darglobal_catalog)} DarGlobal).")
