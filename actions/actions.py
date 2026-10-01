from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

import sqlite3
from datetime import datetime
import os


# =========================
# ตั้งค่า path ของ database (กัน path พัง)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bmi.db")


# =========================
# ฟังก์ชันสร้างและตั้งค่าตั้งต้นสำหรับ SQLite
# =========================
def db_init():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # สร้างตารางประวัติผู้ใช้งาน
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bmi_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            weight REAL,
            height REAL,
            age INTEGER,
            gender TEXT,
            bmi REAL,
            bmr REAL,
            tdee REAL,
            goal TEXT,
            activity TEXT,
            created_at TEXT
        )
        """)

        # เพิ่มคอลัมน์ใหม่กรณีตารางมีอยู่แล้ว
        for col_name, col_type in [("age", "INTEGER"), ("gender", "TEXT"), ("bmr", "REAL"), ("tdee", "REAL")]:
            try:
                cursor.execute(f"ALTER TABLE bmi_history ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

        # สร้างตารางเมนูแนะนำอาหารตามระดับ BMI
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bmi_category TEXT,
            menu_name TEXT,
            calories INTEGER,
            description TEXT,
            image_url TEXT
        )
        """)

        # เพิ่มคอลัมน์ image_url กรณีตารางมีอยู่แล้ว
        try:
            cursor.execute("ALTER TABLE food_recommendations ADD COLUMN image_url TEXT")
        except sqlite3.OperationalError:
            pass

        # ตรวจสอบว่ามีข้อมูลเมนูอาหารอยู่แล้วหรือไม่ ถ้าไม่มีให้นำเข้าตัวอย่างข้อมูล
        cursor.execute("SELECT COUNT(*) FROM food_recommendations")
        count = cursor.fetchone()[0]
        if count == 0:
            foods = [
                # กลุ่ม ผอม (4 เมนู)
                ('ผอม', 'อกไก่ย่างกับข้าวกล้อง', 450, 'เน้นโปรตีนและคาร์โบไฮเดรตเชิงซ้อนเพื่อสร้างกล้ามเนื้ออย่างมีคุณภาพ',
                 'https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=500'),
                ('ผอม', 'ไข่ตุ๋นทรงเครื่อง (ใส่หมูสับและเต้าหู้)', 250, 'อาหารย่อยง่าย โปรตีนสูง เพิ่มพลังงานและสารอาหารที่มีประโยชน์',
                 'https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=500'),
                ('ผอม', 'ข้าวไข่เจียวแกงจืดเต้าหู้หมูสับ', 500, 'จับคู่เพื่อเพิ่มพลังงานและสารอาหารที่ครบถ้วน',
                 'https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=500'),
                ('ผอม', 'สเต๊กปลาแซลมอนย่างคู่กับมันบด', 520, 'โอเมก้า 3 ไขมันดี โปรตีนแน่น ช่วยเพิ่มพลังงานสมดุล',
                 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=500'),

                # กลุ่ม ปกติ (4 เมนู)
                ('ปกติ', 'แกงจืดเต้าหู้หมูสับผักกาดขาว', 180, 'โปรตีนจากเต้าหู้และไขมันต่ำ ช่วยควบคุมน้ำหนักให้อยู่ในเกณฑ์ดี',
                 'https://images.unsplash.com/photo-1547592180-85f173990554?w=500'),
                ('ปกติ', 'ปลาช่อนเผาเกลือคู่กับผักต้ม', 280, 'ได้ไขมันดีและโปรตีนสูงจากเนื้อปลา ช่วยบำรุงกล้ามเนื้อ',
                 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=500'),
                ('ปกติ', 'ข้าวผัดอกไก่ใส่ผักรวม', 420, 'ให้สารอาหารสมดุล ทั้งคาร์โบไฮเดรต โปรตีน และวิตามิน',
                 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=500'),
                ('ปกติ', 'ผัดกะเพราอกไก่ไข่ดาวน้ำ', 350, 'รสชาติจัดจ้าน โปรตีนเน้นๆ ใช้ไข่ดาวน้ำลดไขมันส่วนเกิน',
                 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=500'),

                # กลุ่ม น้ำหนักเกิน (4 เมนู)
                ('น้ำหนักเกิน', 'สลัดอกไก่ฉีกน้ำสลัดใส', 220, 'แคลอรีต่ำ ไฟเบอร์สูงจากผักสด ช่วยคุมระดับพลังงาน',
                 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500'),
                ('น้ำหนักเกิน', 'ยำวุ้นเส้นอกไก่สับ', 250, 'รสจัดจ้าน แคลอรีน้อย โปรตีนเน้นๆ ช่วยกระตุ้นระบบเผาผลาญ',
                 'https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?w=500'),
                ('น้ำหนักเกิน', 'ต้มยำปลากระพงน้ำใส', 150, 'ไม่มีไขมันส่วนเกิน แคลอรีต่ำมาก อิ่มสบายท้อง',
                 'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=500'),
                ('น้ำหนักเกิน', 'เกาเหลาอกไก่หมูสับน้ำใสเน้นผัก', 200, 'อิ่มสบายท้อง ไฟเบอร์สูง คาร์โบไฮเดรตต่ำ',
                 'https://images.unsplash.com/photo-1604908177522-7894ff61bee2?w=500'),

                # กลุ่ม อ้วน (4 เมนู)
                ('อ้วน', 'แกงส้มผักรวม', 120, 'แคลอรีต่ำมาก ไม่มีน้ำมัน มีกากใยผักช่วยในการขับถ่ายและให้อิ่มนาน',
                 'https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=500'),
                ('อ้วน', 'สุกี้น้ำอกไก่ (เน้นผัก/วุ้นเส้นน้อย)', 180, 'เน้นโปรตีนและกากใย หลีกเลี่ยงคาร์โบไฮเดรตและไขมันส่วนเกิน',
                 'https://images.unsplash.com/photo-1547592166-23ac45744acd?w=500'),
                ('อ้วน', 'ลาบเต้าหู้ขาว', 140, 'โปรตีนจากพืช ไขมันต่ำ โซเดียมปานกลาง ดีต่อการควบคุมน้ำหนักเป็นพิเศษ',
                 'https://images.unsplash.com/photo-1540420773420-3366772f4999?w=500'),
                ('อ้วน', 'ซุปอกไก่ไส้ผักกาดขาว', 110, 'แคลอรีต่ำเป็นพิเศษ อบอุ่นท้อง ช่วยคุมแคลอรีได้อย่างดีเยี่ยม',
                 'https://images.unsplash.com/photo-1547592530-34ca352e05ca?w=500'),
            ]
            cursor.executemany(
                "INSERT INTO food_recommendations (bmi_category, menu_name, calories, description, image_url) VALUES (?, ?, ?, ?, ?)",
                foods
            )
            conn.commit()

        # อัปเดตรูปภาพให้ตรงกับชื่อเมนูในฐานข้อมูลที่มีอยู่แล้ว
        image_updates = [
            ('https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=500', 'อกไก่ย่างกับข้าวกล้อง'),
            ('https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=500', 'ไข่ตุ๋นทรงเครื่อง (ใส่หมูสับและเต้าหู้)'),
            ('https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=500', 'ข้าวไข่เจียวแกงจืดเต้าหู้หมูสับ'),
            ('https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=500', 'สเต๊กปลาแซลมอนย่างคู่กับมันบด'),
            ('https://images.unsplash.com/photo-1547592180-85f173990554?w=500', 'แกงจืดเต้าหู้หมูสับผักกาดขาว'),
            ('https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=500', 'ปลาช่อนเผาเกลือคู่กับผักต้ม'),
            ('https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=500', 'ข้าวผัดอกไก่ใส่ผักรวม'),
            ('https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=500', 'ผัดกะเพราอกไก่ไข่ดาวน้ำ'),
            ('https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500', 'สลัดอกไก่ฉีกน้ำสลัดใส'),
            ('https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?w=500', 'ยำวุ้นเส้นอกไก่สับ'),
            ('https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=500', 'ต้มยำปลากระพงน้ำใส'),
            ('https://images.unsplash.com/photo-1604908177522-7894ff61bee2?w=500', 'เกาเหลาอกไก่หมูสับน้ำใสเน้นผัก'),
            ('https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=500', 'แกงส้มผักรวม'),
            ('https://images.unsplash.com/photo-1547592166-23ac45744acd?w=500', 'สุกี้น้ำอกไก่ (เน้นผัก/วุ้นเส้นน้อย)'),
            ('https://images.unsplash.com/photo-1540420773420-3366772f4999?w=500', 'ลาบเต้าหู้ขาว'),
            ('https://images.unsplash.com/photo-1547592530-34ca352e05ca?w=500', 'ซุปอกไก่ไส้ผักกาดขาว'),
        ]
        for img_url, menu_name in image_updates:
            cursor.execute(
                "UPDATE food_recommendations SET image_url = ? WHERE menu_name = ?",
                (img_url, menu_name)
            )
        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Error initializing database: {e}")


# เรียกใช้งานตอนโหลดโมดูล
db_init()



# =========================================================
# Helper Functions สำหรับสร้าง LINE Flex Message JSON Structure
# =========================================================

def build_health_flex_card(gender_str, age, weight, height, bmi, bmi_level, bmr, tdee, target_cal, goal_desc, water_l, water_glasses, protein_g, carbs_g, fat_g):
    color_map = {
        "ผอม": "#0288D1",
        "ปกติ": "#2E7D32",
        "น้ำหนักเกิน": "#F57C00",
        "อ้วน": "#D32F2F"
    }
    bg_color = color_map.get(bmi_level, "#2E7D32")

    flex_json = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": bg_color,
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "text",
                    "text": "📊 รายงานสุขภาพ & โภชนาการ",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "lg"
                },
                {
                    "type": "text",
                    "text": f"👤 เพศ {gender_str} | อายุ {int(age)} ปี | {weight} kg | {height} cm",
                    "color": "#E0E0E0",
                    "size": "xs",
                    "margin": "xs"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "backgroundColor": "#F5F5F5",
                    "cornerRadius": "md",
                    "paddingAll": "10px",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "ค่า BMI ของคุณ", "size": "xs", "color": "#757575"},
                                {"type": "text", "text": f"{bmi}", "size": "xxl", "weight": "bold", "color": bg_color}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "เกณฑ์ดัชนีมวลกาย", "size": "xs", "color": "#757575"},
                                {"type": "text", "text": f"เกณฑ์: {bmi_level}", "size": "md", "weight": "bold", "color": bg_color, "margin": "xs"}
                            ]
                        }
                    ]
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "⚡ BMR (อัตราเผาผลาญพัก):", "size": "xs", "color": "#666666", "flex": 3},
                                {"type": "text", "text": f"{bmr:.0f} kcal", "size": "xs", "weight": "bold", "color": "#333333", "align": "end", "flex": 2}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "🔥 TDEE (พลังงานใช้จริง):", "size": "xs", "color": "#666666", "flex": 3},
                                {"type": "text", "text": f"{tdee:.0f} kcal", "size": "xs", "weight": "bold", "color": "#333333", "align": "end", "flex": 2}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": f"🎯 แนะนำ ({goal_desc}):", "size": "xs", "color": "#1565C0", "weight": "bold", "flex": 3},
                                {"type": "text", "text": f"{target_cal} kcal", "size": "sm", "weight": "bold", "color": "#D32F2F", "align": "end", "flex": 2}
                            ]
                        }
                    ]
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": [
                        {"type": "text", "text": "🥗 สารอาหารหลักต่อวัน (Macros):", "size": "xs", "weight": "bold", "color": "#333333"},
                        {
                            "type": "text",
                            "text": f"• โปรตีน: {protein_g}g | คาร์บ: {carbs_g}g | ไขมัน: {fat_g}g",
                            "size": "xs",
                            "color": "#555555"
                        },
                        {"type": "text", "text": f"💧 น้ำดื่มต่อวัน: ~{water_l} ลิตร ({water_glasses} แก้ว)", "size": "xs", "weight": "bold", "color": "#0288D1", "margin": "xs"}
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#2E7D32",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "🍽️ เมนูอาหาร",
                        "text": "แนะนำอาหารหน่อย"
                    }
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#1565C0",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "🏋️ ออกกำลังกาย",
                        "text": "แนะนำการออกกำลังกายหน่อย"
                    }
                }
            ]
        }
    }
    return {
        "type": "flex",
        "alt_text": f"📊 ผลการประเมินสุขภาพของคุณ: BMI {bmi} ({bmi_level})",
        "flex_contents": flex_json
    }


def build_food_flex_card(bmi_category, menu_name, calories, description, image_url=None):
    if not image_url:
        image_url = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500"

    flex_json = {
        "type": "bubble",
        "size": "mega",
        "hero": {
            "type": "image",
            "url": image_url,
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"กลุ่ม: {bmi_category}",
                            "size": "xs",
                            "color": "#1565C0",
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": f"🔥 {calories} kcal",
                            "size": "xs",
                            "color": "#D32F2F",
                            "weight": "bold",
                            "align": "end"
                        }
                    ]
                },
                {
                    "type": "text",
                    "text": menu_name,
                    "weight": "bold",
                    "size": "lg",
                    "color": "#111111",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": description,
                    "size": "xs",
                    "color": "#666666",
                    "wrap": True,
                    "maxLines": 3
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "color": "#E8F5E9",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "🔄 สุ่มเมนูอาหารใหม่",
                        "text": "แนะนำอาหารหน่อย"
                    }
                }
            ]
        }
    }
    return {
        "type": "flex",
        "alt_text": f"🍽️ เมนูอาหารแนะนำ: {menu_name} ({calories} kcal)",
        "flex_contents": flex_json
    }


def build_workout_carousel_flex(goal_cat, bmi_level):
    cards = [
        {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#1565C0",
                "contents": [
                    {"type": "text", "text": "🏃‍♂️ ตารางคาร์ดิโอ & แอโรบิก", "color": "#FFFFFF", "weight": "bold", "size": "sm"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {"type": "text", "text": f"🎯 เป้าหมาย: {goal_cat}", "size": "xs", "weight": "bold", "color": "#1565C0"},
                    {"type": "text", "text": "• ความถี่: 3-5 วัน/สัปดาห์", "size": "xs", "color": "#333333"},
                    {"type": "text", "text": "• กิจกรรม: วิ่งเหยาะๆ, ปั่นจักรยาน, เดินเร็วบนทางชัน, ว่ายน้ำ", "size": "xs", "color": "#666666", "wrap": True},
                    {"type": "text", "text": "• ก้าวเดิน: 8,000 - 10,000 ก้าว/วัน", "size": "xs", "color": "#2E7D32", "weight": "bold", "margin": "xs"}
                ]
            }
        },
        {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#D32F2F",
                "contents": [
                    {"type": "text", "text": "🏋️‍♂️ ตารางเวทเทรนนิ่ง (Strength)", "color": "#FFFFFF", "weight": "bold", "size": "sm"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {"type": "text", "text": "📅 ตาราง 4 วัน/สัปดาห์:", "size": "xs", "weight": "bold", "color": "#D32F2F"},
                    {"type": "text", "text": "• จันทร์: อก, ไหล่, หลังแขน", "size": "xs", "color": "#333333"},
                    {"type": "text", "text": "• อังคาร: หลัง, ไหล่หลัง, หน้าแขน", "size": "xs", "color": "#333333"},
                    {"type": "text", "text": "• พฤหัส: ต้นขา, ก้น, น่อง", "size": "xs", "color": "#333333"},
                    {"type": "text", "text": "• ศุกร์: แกนกลางลำตัว (Core)", "size": "xs", "color": "#333333"}
                ]
            }
        },
        {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#2E7D32",
                "contents": [
                    {"type": "text", "text": "🧘‍♀️ การยืดเหยียด & ข้อควรระวัง", "color": "#FFFFFF", "weight": "bold", "size": "sm"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {"type": "text", "text": f"⚠️ กลุ่ม BMI: {bmi_level}", "size": "xs", "weight": "bold", "color": "#2E7D32"},
                    {"type": "text", "text": "• ยืดเหยียดกล้ามเนื้อก่อนและหลังออกกำลังกายทุกครั้ง 5-10 นาที", "size": "xs", "color": "#555555", "wrap": True},
                    {"type": "text", "text": "• นอนหลับพักผ่อน 7-8 ชั่วโมงต่อคืนเพื่อการฟื้นฟู", "size": "xs", "color": "#555555", "wrap": True}
                ]
            }
        }
    ]

    flex_carousel = {
        "type": "carousel",
        "contents": cards
    }

    return {
        "type": "flex",
        "alt_text": f"💪 ตารางออกกำลังกายแนะนำ ({goal_cat})",
        "flex_contents": flex_carousel
    }




class ActionCalculateBMI(Action):

    def name(self) -> Text:
        return "action_calculate_bmi"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # =========================
        # 1️⃣ ดึงค่าจาก slot
        # =========================
        user_id = tracker.sender_id
        weight = tracker.get_slot("weight")
        height = tracker.get_slot("height")
        goal = tracker.get_slot("goal")
        activity = tracker.get_slot("activity_level")

        # ========================================================
        # ระบบป้องกันสกัดค่า (Entity Extraction) สลับที่กัน หรือตกหล่น
        # ========================================================
        import re
        raw_text = tracker.latest_message.get("text", "")
        found_nums = []
        for n in re.findall(r"\d+\.?\d*", raw_text):
            try:
                found_nums.append(float(n))
            except ValueError:
                pass

        if len(found_nums) >= 2:
            # คัดแยกส่วนสูง (มักจะ >= 100 cm) และน้ำหนัก
            heights = [n for n in found_nums if n >= 100]
            weights = [n for n in found_nums if n < 100]

            if heights and weights:
                height = max(heights)
                weight = max(weights)  # เลือกค่าน้ำหนักที่สมเหตุสมผลที่สุด
            else:
                sorted_nums = sorted(found_nums)
                height = sorted_nums[-1]
                weight = sorted_nums[-2] if len(sorted_nums) >= 2 else sorted_nums[0]
        else:
            # Fallback ดึงจาก slot เดิมหากมี
            if weight is None or height is None:
                pass



        # =========================
        # 2️⃣ ตรวจสอบข้อมูล (กัน None)
        # =========================
        if weight is None or height is None:
            dispatcher.utter_message(
                text="❗ ข้อมูลยังไม่ครบ\nกรุณากรอกในรูปแบบ: น้ำหนัก ส่วนสูง เป้าหมาย ระดับกิจกรรม\nตัวอย่าง: 52 165 ลดน้ำหนัก เบา"
            )
            return []

        # =========================
        # 3️⃣ แปลงเป็นตัวเลข (กัน TypeError)
        # =========================
        try:
            weight = float(weight)
            height = float(height)
        except (TypeError, ValueError):
            dispatcher.utter_message(
                text="❗ น้ำหนักและส่วนสูงต้องเป็นตัวเลข\nตัวอย่าง: 52 165"
            )
            return []

        # =========================
        # 4️⃣ ตรวจสอบค่าที่ผิดปกติ
        # =========================
        if height <= 0 or weight <= 0:
            dispatcher.utter_message(
                text="❗ น้ำหนักและส่วนสูงต้องมากกว่า 0"
            )
            return []

        # =========================
        # 5️⃣ คำนวณ BMI
        # =========================
        bmi = round(weight / ((height / 100) ** 2), 2)

        # =========================
        # 6️⃣ แปลผล BMI
        # =========================
        if bmi < 18.5:
            bmi_level = "ผอม"
            advice = "ควรเพิ่มโภชนาการและออกกำลังกายเบา ๆ เช่น เดินหรือยืดเหยียด"
        elif bmi < 23:
            bmi_level = "ปกติ"
            advice = "ออกกำลังกายระดับปานกลาง เช่น เดินเร็ววันละ 30 นาที"
        elif bmi < 25:
            bmi_level = "น้ำหนักเกิน"
            advice = "ควรออกกำลังกายแบบคาร์ดิโอและควบคุมอาหาร"
        else:
            bmi_level = "อ้วน"
            advice = "เริ่มออกกำลังกายเบา ๆ อย่างสม่ำเสมอ และควบคุมอาหาร"

        goal = goal or "รักษารูปร่าง"
        activity = activity or "ปานกลาง"

        # =========================
        # 7️⃣ บันทึกประวัติลง SQLite (Safe)
        # =========================
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS bmi_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                weight REAL,
                height REAL,
                bmi REAL,
                goal TEXT,
                activity TEXT,
                created_at TEXT
            )
            """)

            cursor.execute(
                "SELECT bmi FROM bmi_history WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            last = cursor.fetchone()

            cursor.execute("""
            INSERT INTO bmi_history
            (user_id, weight, height, bmi, goal, activity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                weight,
                height,
                bmi,
                goal,
                activity,
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            dispatcher.utter_message(
                text="⚠️ เกิดข้อผิดพลาดในการบันทึกข้อมูล แต่ยังสามารถคำนวณ BMI ได้"
            )
            last = None

        # =========================
        # 8️⃣ สรุปผล + เปรียบเทียบครั้งก่อน
        # =========================
        if last:
            diff = round(bmi - last[0], 2)
            history_text = f"\n📈 เปลี่ยนจากครั้งก่อน: {diff}"
        else:
            history_text = "\n🗂️ นี่คือการบันทึกข้อมูลครั้งแรกของคุณ"

        bmr_est = round(10 * weight + 6.25 * height - 120, 1)
        tdee_est = round(bmr_est * 1.375, 1)
        target_cal_est = round(tdee_est)
        water_l_est = round(weight * 33 / 1000, 2)
        water_glasses_est = round(weight * 33 / 250)
        protein_est = round(weight * 2.0)
        carbs_est = round(weight * 2.5)
        fat_est = round(weight * 0.8)

        flex_payload = build_health_flex_card(
            "ทั่วไป", 25, weight, height, bmi, bmi_level,
            bmr_est, tdee_est, target_cal_est, goal, water_l_est, water_glasses_est,
            protein_est, carbs_est, fat_est
        )

        dispatcher.utter_message(
            text=(
                f"📊 ผลการประเมินสุขภาพ\n"
                f"- BMI: {bmi}\n"
                f"- อยู่ในกลุ่ม: {bmi_level}\n"
                f"- เป้าหมาย: {goal}\n"
                f"- ระดับกิจกรรม: {activity}"
                f"{history_text}\n\n"
                f"💪 คำแนะนำ:\n{advice}\n\n"
                f"ℹ️ ข้อมูลนี้เป็นคำแนะนำเบื้องต้น ไม่ใช่การวินิจฉัยทางการแพทย์"
            ),
            custom=flex_payload
        )


        return []


# =================================
# Action สำหรับแนะนำอาหารตามค่า BMI ล่าสุด
# =================================
class ActionRecommendFood(Action):

    def name(self) -> Text:
        return "action_recommend_food"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        user_id = tracker.sender_id

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # ดึงประวัติคำนวณ BMI ล่าสุด
            cursor.execute(
                "SELECT bmi FROM bmi_history WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            last_record = cursor.fetchone()

            if not last_record:
                dispatcher.utter_message(
                    text=(
                        "⚠️ ยังไม่พบประวัติการคำนวณ BMI ของคุณในระบบค่ะ\n"
                        "กรุณากรอกข้อมูลของคุณเพื่อประเมินสุขภาพก่อนนะคะ\n"
                        "ตัวอย่างการกรอก: น้ำหนัก ส่วนสูง เป้าหมาย ระดับกิจกรรม (เช่น 52 165 ลดน้ำหนัก เบา)"
                    )
                )
                conn.close()
                return []

            bmi_val = last_record[0]
            bmi = float(bmi_val) if bmi_val is not None else 22.0

            # แปลผลระดับ BMI เพื่อเลือกประเภทอาหาร
            if bmi < 18.5:
                bmi_level = "ผอม"
            elif bmi < 23:
                bmi_level = "ปกติ"
            elif bmi < 25:
                bmi_level = "น้ำหนักเกิน"
            else:
                bmi_level = "อ้วน"

            last_food = tracker.get_slot("last_food_menu")

            # สุ่มเลือกเมนูอาหาร 1 อย่าง โดยพยายามไม่ซ้ำกับเมนูเดิม
            cursor.execute(
                "SELECT menu_name, calories, description, image_url FROM food_recommendations WHERE bmi_category=? AND menu_name != ? ORDER BY RANDOM() LIMIT 1",
                (bmi_level, str(last_food or ""))
            )
            food_record = cursor.fetchone()

            # หากไม่พบเมนูอื่น ให้สุ่มจากหมวดหมู่นั้นๆ โดยตรง
            if not food_record:
                cursor.execute(
                    "SELECT menu_name, calories, description, image_url FROM food_recommendations WHERE bmi_category=? ORDER BY RANDOM() LIMIT 1",
                    (bmi_level,)
                )
                food_record = cursor.fetchone()

            conn.close()

            if food_record:
                menu_name = food_record[0]
                calories = food_record[1]
                description = food_record[2]
                image_url = food_record[3] if len(food_record) > 3 else None

                flex_payload = build_food_flex_card(bmi_level, menu_name, calories, description, image_url)
                dispatcher.utter_message(
                    text=(
                        f"🍽️ เมนูแนะนำสำหรับคุณ (กลุ่มดัชนีมวลกาย: {bmi_level})\n"
                        f"✨ **{menu_name}** ({calories} kcal)\n"
                        f"📝 {description}"
                    ),
                    custom=flex_payload
                )
                return [SlotSet("last_food_menu", menu_name)]
            else:
                dispatcher.utter_message(
                    text="ขออภัยค่ะ ไม่พบข้อมูลเมนูแนะนำสำหรับกลุ่มนี้ในฐานข้อมูล"
                )

        except Exception as e:
            dispatcher.utter_message(
                text=f"⚠️ เกิดข้อผิดพลาดในการดึงข้อมูลเมนูอาหารแนะนำ"
            )

        return []



# =========================================================
# Action คำนวณค่าทางสุขภาพแบบละเอียด (BMR, TDEE, Water, Macros)
# =========================================================
class ActionCalculateHealthMetrics(Action):

    def name(self) -> Text:
        return "action_calculate_health_metrics"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        user_id = tracker.sender_id
        weight = tracker.get_slot("weight")
        height = tracker.get_slot("height")
        age = tracker.get_slot("age")
        gender = tracker.get_slot("gender")
        goal = tracker.get_slot("goal") or "รักษารูปร่าง"
        activity = tracker.get_slot("activity_level") or "ปานกลาง"

        raw_text = tracker.latest_message.get("text", "")

        # ---------------------------------------------------------
        # สกัด gender และ age เพิ่มเติมหาก Slot ยังว่างอยู่
        # ---------------------------------------------------------
        if not gender:
            if any(w in raw_text for w in ["หญิง", "ผู้หญิง", "ผญ", "female", "woman"]):
                gender = "หญิง"
            elif any(w in raw_text for w in ["ชาย", "ผู้ชาย", "ผช", "male", "man"]):
                gender = "ชาย"
            else:
                gender = "ชาย"  # ค่าเริ่มต้นหากไม่ระบุ

        import re
        numeric_values = []
        for val in [age, weight, height]:
            if val is not None:
                try:
                    numeric_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        if len(numeric_values) < 3:
            found_nums = re.findall(r"\d+\.?\d*", raw_text)
            if len(found_nums) >= 3:
                try:
                    numeric_values = [float(n) for n in found_nums[:3]]
                except ValueError:
                    pass

        # จัดสรรค่าตัวเลข: ตัวอย่าง [25, 70, 175] -> age=25, weight=70, height=175
        if len(numeric_values) >= 3:
            sorted_nums = sorted(numeric_values)
            if sorted_nums[-1] > 100:
                height = sorted_nums[-1]
                val1, val2 = sorted_nums[0], sorted_nums[1]
                if 10 <= val1 <= 95 and val2 > val1:
                    age = val1
                    weight = val2
                else:
                    weight = val1
                    age = val2
            else:
                age, weight, height = numeric_values[0], numeric_values[1], numeric_values[2]
        elif len(numeric_values) == 2:
            val1, val2 = numeric_values[0], numeric_values[1]
            weight = min(val1, val2)
            height = max(val1, val2)
            if age is None:
                age = 25.0

        if weight is None or height is None:
            dispatcher.utter_message(
                text="❗ ข้อมูลไม่ครบถ้วนค่ะ\nกรุณากรอกในรูปแบบ: เพศ อายุ น้ำหนัก ส่วนสูง เป้าหมาย ระดับกิจกรรม\nตัวอย่าง: ชาย 25 70 175 ลดน้ำหนัก ปานกลาง"
            )
            return []

        try:
            weight = float(weight)
            height = float(height)
            age = float(age) if age is not None else 25.0
        except (TypeError, ValueError):
            dispatcher.utter_message(text="❗ อายุ น้ำหนัก และส่วนสูงต้องเป็นตัวเลขค่ะ")
            return []

        if height <= 0 or weight <= 0 or age <= 0:
            dispatcher.utter_message(text="❗ ข้อมูลตัวเลขต้องมากกว่า 0 ค่ะ")
            return []

        # ---------------------------------------------------------
        # 1. คำนวณ BMI
        # ---------------------------------------------------------
        bmi = round(weight / ((height / 100) ** 2), 2)
        if bmi < 18.5:
            bmi_level = "ผอม"
        elif bmi < 23:
            bmi_level = "ปกติ"
        elif bmi < 25:
            bmi_level = "น้ำหนักเกิน"
        else:
            bmi_level = "อ้วน"

        # ---------------------------------------------------------
        # 2. คำนวณ BMR (Mifflin-St Jeor Equation)
        # ---------------------------------------------------------
        is_female = any(w in str(gender).lower() for w in ["หญิง", "female", "woman", "ผู้หญิง", "ผญ"])
        if is_female:
            gender_str = "หญิง"
            bmr = round(10 * weight + 6.25 * height - 5 * age - 161, 1)
        else:
            gender_str = "ชาย"
            bmr = round(10 * weight + 6.25 * height - 5 * age + 5, 1)

        # ---------------------------------------------------------
        # 3. คำนวณ TDEE
        # ---------------------------------------------------------
        act_str = str(activity).lower()
        if any(w in act_str for w in ["เบา", "น้อย", "sedentary", "light"]):
            act_mult = 1.2
        elif any(w in act_str for w in ["หนักมาก", "very active"]):
            act_mult = 1.75
        elif any(w in act_str for w in ["หนัก", "active"]):
            act_mult = 1.6
        else:
            act_mult = 1.375

        tdee = round(bmr * act_mult, 1)

        # ---------------------------------------------------------
        # 4. พลังงานที่แนะนำตามเป้าหมาย (Target Calories)
        # ---------------------------------------------------------
        goal_str = str(goal).lower()
        if any(w in goal_str for w in ["ลด", "คุมความอ้วน", "ไดเอท"]):
            target_cal = round(tdee - 500)
            goal_desc = "ลดน้ำหนัก (ขาดดุลพลังงาน ~500 kcal)"
        elif any(w in goal_str for w in ["เพิ่ม", "กล้ามเนื้อ", "สร้างกล้าม"]):
            target_cal = round(tdee + 300)
            goal_desc = "เพิ่มกล้ามเนื้อ/น้ำหนัก (+300 kcal)"
        else:
            target_cal = round(tdee)
            goal_desc = "รักษารูปร่าง/คงน้ำหนัก"

        # ---------------------------------------------------------
        # 5. สารอาหารหลัก (Macros)
        # ---------------------------------------------------------
        protein_g = round(weight * 2.0)
        protein_kcal = protein_g * 4
        fat_g = round((target_cal * 0.25) / 9)
        fat_kcal = fat_g * 9
        carbs_g = max(0, round((target_cal - protein_kcal - fat_kcal) / 4))

        # ---------------------------------------------------------
        # 6. ปริมาณน้ำดื่มต่อวัน (Daily Water Intake)
        # ---------------------------------------------------------
        water_ml = round(weight * 33)
        water_l = round(water_ml / 1000, 2)
        water_glasses = round(water_ml / 250)

        # ---------------------------------------------------------
        # 7. บันทึกลง SQLite
        # ---------------------------------------------------------
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO bmi_history
            (user_id, weight, height, age, gender, bmi, bmr, tdee, goal, activity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, weight, height, int(age), gender_str,
                bmi, bmr, tdee, str(goal), str(activity),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving health metrics: {e}")

        # ---------------------------------------------------------
        # 8. แสดงผลสรุป ( Text + LINE Flex Card )
        # ---------------------------------------------------------
        flex_payload = build_health_flex_card(
            gender_str, age, weight, height, bmi, bmi_level,
            bmr, tdee, target_cal, goal_desc, water_l, water_glasses,
            protein_g, carbs_g, fat_g
        )

        dispatcher.utter_message(
            text=(
                f"📊 **ผลการประเมินสุขภาพและโภชนาการ**\n"
                f"──────────────────────────\n"
                f"👤 **ข้อมูล:** เพศ {gender_str} | อายุ {int(age)} ปี | น้ำหนัก {weight} kg | ส่วนสูง {height} cm\n"
                f"🎯 **เป้าหมาย:** {goal_desc}\n\n"
                f"📈 **ดัชนีทางสุขภาพ:**\n"
                f"• **BMI:** {bmi} ({bmi_level})\n"
                f"• **BMR (อัตราเผาผลาญขั้นต่ำ):** {bmr:.0f} kcal/วัน\n"
                f"• **TDEE (พลังงานใช้จริงต่อวัน):** {tdee:.0f} kcal/วัน\n\n"
                f"🔥 **พลังงานที่แนะนำต่อวัน:** {target_cal} kcal\n\n"
                f"🥗 **สารอาหารหลักแนะนำ (Macros):**\n"
                f"• โปรตีน: {protein_g} กรัม\n"
                f"• คาร์โบไฮเดรต: {carbs_g} กรัม\n"
                f"• ไขมันดี: {fat_g} กรัม\n\n"
                f"💧 **ปริมาณน้ำดื่มที่แนะนำต่อวัน:**\n"
                f"• ประมาณ {water_l} ลิตร (~{water_glasses} แก้ว)\n\n"
                f"ℹ️ ข้อมูลนี้เป็นคำแนะนำเบื้องต้น ไม่ใช่คำวินิจฉัยทางการแพทย์ค่ะ"
            ),
            custom=flex_payload
        )

        return []



# =========================================================
# Action แนะนำการออกกำลังกายตามเป้าหมาย และระดับ BMI
# =========================================================
class ActionRecommendWorkout(Action):

    def name(self) -> Text:
        return "action_recommend_workout"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        user_id = tracker.sender_id
        slot_goal = tracker.get_slot("goal")
        slot_activity = tracker.get_slot("activity_level")

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # ดึงประวัติคำนวณล่าสุดของผู้ใช้
            cursor.execute(
                "SELECT bmi, goal, activity FROM bmi_history WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            last_record = cursor.fetchone()
            conn.close()

            if last_record:
                bmi_val, history_goal, history_activity = last_record
                bmi = float(bmi_val) if bmi_val is not None else 22.0
                goal = slot_goal or history_goal or "รักษารูปร่าง"
                activity = slot_activity or history_activity or "ปานกลาง"
            else:
                bmi = 22.0  # ค่าปกติถ้ายังไม่มีประวัติ
                goal = slot_goal or "รักษารูปร่าง"
                activity = slot_activity or "ปานกลาง"

            # แปลหมวดหมู่ BMI
            if bmi < 18.5:
                bmi_level = "ผอม"
            elif bmi < 23:
                bmi_level = "ปกติ"
            elif bmi < 25:
                bmi_level = "น้ำหนักเกิน"
            else:
                bmi_level = "อ้วน"

            goal_lower = str(goal).lower()

            if any(w in goal_lower for w in ["ลด", "คุมความอ้วน", "ไดเอท"]):
                goal_cat = "ลดน้ำหนัก/ลดไขมัน"
                if bmi_level in ["น้ำหนักเกิน", "อ้วน"]:
                    workout_plan = (
                        "🏃‍♂️ **ตารางออกกำลังกายแนะนำ (เน้นลดไขมัน + ถนอมข้อเข่า):**\n"
                        "• **รูปแบบ:** Low-Impact Cardio (แรงกระแทกต่ำ) ผสม Weight Training\n"
                        "• **ความถี่:** 4-5 วัน/สัปดาห์ (วันละ 30-45 นาที)\n\n"
                        "📅 **ตารางประจำสัปดาห์:**\n"
                        "- **จันทร์/พุธ/ศุกร์:** คาร์ดิโอแรงกระแทกต่ำ (ปั่นจักรยาน, ว่ายน้ำ, เดินเร็วบนสายพานชัน 10-15%)\n"
                        "- **อังคาร/พฤหัส:** เวทเทรนนิ่งเน้นกล้ามเนื้อมวนใหญ่ (Squat, Push-up, Dumbbell Row)\n"
                        "- **เสาร์/อาทิตย์:** พักผ่อน หรือยืดเหยียดกล้ามเนื้อ (Stretching / Yoga)\n\n"
                        "⚠️ **ข้อควรระวัง:** หลีกเลี่ยงการกระโดดหรือวิ่งบนพื้นแข็ง เพื่อป้องกันการบาดเจ็บที่ข้อเข่าและข้อเท้า\n"
                        "🚶 **เป้าหมายก้าวเดิน:** 8,000 - 10,000 ก้าว/วัน"
                    )
                else:
                    workout_plan = (
                        "🏃‍♂️ **ตารางออกกำลังกายแนะนำ (เน้นเผาผลาญไขมัน):**\n"
                        "• **รูปแบบ:** Cardio Zone 2 / HIIT ผสม Weight Training\n"
                        "• **ความถี่:** 4-5 วัน/สัปดาห์ (วันละ 45-60 นาที)\n\n"
                        "📅 **ตารางประจำสัปดาห์:**\n"
                        "- **จันทร์/พฤหัส:** เวทเทรนนิ่ง Upper Body (อก, หลัง, ไหล่, แขน)\n"
                        "- **อังคาร/ศุกร์:** เวทเทรนนิ่ง Lower Body (ขา, ก้น, แกนกลางลำตัว)\n"
                        "- **พุธ/เสาร์:** คาร์ดิโอโซน 2 (วิ่งเหยาะๆ หรือปั่นจักรยานต่อเนื่อง 45 นาที)\n"
                        "- **อาทิตย์:** พักผ่อน (Rest Day)\n\n"
                        "🚶 **เป้าหมายก้าวเดิน:** 10,000 ก้าว/วัน"
                    )

            elif any(w in goal_lower for w in ["เพิ่ม", "กล้ามเนื้อ", "สร้างกล้าม"]):
                goal_cat = "เพิ่มกล้ามเนื้อ"
                workout_plan = (
                    "🏋️‍♂️ **ตารางออกกำลังกายแนะนำ (เน้นสร้างมวลกล้ามเนื้อ - Hypertrophy):**\n"
                    "• **รูปแบบ:** Progressive Overload Resistance Training (เล่นเวทแรงต้านเพิ่มขึ้นเรื่อยๆ)\n"
                    "• **ความถี่:** 4 วัน/สัปดาห์ (วันละ 45-60 นาที)\n\n"
                    "📅 **ตารางประจำสัปดาห์:**\n"
                    "- **จันทร์:** Push Day (อก, ไหล่หน้า/ข้าง, หลังแขน)\n"
                    "- **อังคาร:** Pull Day (หลัง, ไหล่หลัง, หน้าแขน)\n"
                    "- **พุธ:** พักผ่อน หรือยืดเหยียด\n"
                    "- **พฤหัส:** Leg Day (ต้นขาหน้า, ต้นขาหลัง, น่อง, ก้น)\n"
                    "- **ศุกร์:** Core & Full Body / เล่นจุดเน้น\n"
                    "- **เสาร์/อาทิตย์:** พักผ่อนเพื่อฟื้นฟูกล้ามเนื้อ\n\n"
                    "💡 **คำแนะนำเพิ่มเติม:** งดคาร์ดิโอหนักเกินไป เน้นทานโปรตีนให้เพียงพอและนอนหลับ 7-8 ชม./วัน"
                )

            else:
                goal_cat = "รักษารูปร่าง/สุขภาพ"
                workout_plan = (
                    "🧘‍♀️ **ตารางออกกำลังกายแนะนำ (เพื่อสุขภาพและสร้างความแข็งแรง):**\n"
                    "• **รูปแบบ:** Moderate Cardio + Resistance Training\n"
                    "• **ความถี่:** 3-4 วัน/สัปดาห์ (วันละ 30-45 นาที)\n\n"
                    "📅 **ตารางประจำสัปดาห์:**\n"
                    "- **จันทร์/พุธ:** คาร์ดิโอระดับปานกลาง (วิ่งเหยาะๆ, ว่ายน้ำ, เต้นแอโรบิก)\n"
                    "- **อังคาร/พฤหัส:** บอดี้เวท / เล่นเวทน้ำหนักปานกลาง (12-15 ครั้ง/เซ็ต)\n"
                    "- **ศุกร์/เสาร์:** โยคะ, พิลาทิส หรือกิจกรรมนันทนาการที่ชอบ\n"
                    "- **อาทิตย์:** พักผ่อน\n\n"
                    "🚶 **เป้าหมายก้าวเดิน:** 7,000 - 8,000 ก้าว/วัน"
                )

            note_history = ""
            if not last_record:
                note_history = "\n\n💡 *ข้อแนะนำ: คุณสามารถพิมพ์ข้อมูล เพศ อายุ น้ำหนัก ส่วนสูง เป้าหมาย เพื่อให้บอทปรับแผนการออกกำลังกายให้แม่นยำยิ่งขึ้นได้นะคะ*"

            flex_payload = build_workout_carousel_flex(goal_cat, bmi_level)

            dispatcher.utter_message(
                text=(
                    f"💪 **คำแนะนำการออกกำลังกายส่วนบุคคล**\n"
                    f"──────────────────────────\n"
                    f"🎯 **เป้าหมาย:** {goal_cat} | **กลุ่ม BMI:** {bmi_level}\n\n"
                    f"{workout_plan}"
                    f"{note_history}"
                ),
                custom=flex_payload
            )

        except Exception as e:
            dispatcher.utter_message(
                text="⚠️ เกิดข้อผิดพลาดในการดึงคำแนะนำการออกกำลังกาย"
            )

        return []


# =========================================================
# Helper: สร้าง LINE Flex Message สำหรับประวัติ BMI
# =========================================================

def build_bmi_history_flex_card(records):
    """
    records: list of tuples (created_at, weight, height, bmi, goal)
              เรียงจากใหม่ไปเก่า (ล่าสุดก่อน)
    """
    color_map = {
        "ผอม": "#0288D1",
        "ปกติ": "#2E7D32",
        "น้ำหนักเกิน": "#F57C00",
        "อ้วน": "#D32F2F"
    }

    def bmi_level_info(bmi_val):
        if bmi_val < 18.5:
            return "ผอม", "📘"
        elif bmi_val < 23:
            return "ปกติ", "💚"
        elif bmi_val < 25:
            return "น้ำหนักเกิน", "🟠"
        else:
            return "อ้วน", "🔴"

    # คำนวณแนวโน้ม
    if len(records) >= 2:
        first_bmi = float(records[-1][3]) if records[-1][3] else 22.0
        latest_bmi = float(records[0][3]) if records[0][3] else 22.0
        diff = round(latest_bmi - first_bmi, 2)
        if diff < -0.5:
            trend_text = f"📉 BMI ลดลง {abs(diff):.2f} จากครั้งแรก — ดีมากค่ะ!"
            trend_color = "#2E7D32"
        elif diff > 0.5:
            trend_text = f"📈 BMI เพิ่มขึ้น {diff:.2f} จากครั้งแรก"
            trend_color = "#D32F2F"
        else:
            trend_text = f"➡️ BMI คงที่ (เปลี่ยนแปลง {diff:+.2f})"
            trend_color = "#F57C00"
    else:
        trend_text = "🗂️ บันทึกข้อมูลครั้งแรก — ติดตามต่อเนื่องเพื่อดูพัฒนาการ!"
        trend_color = "#1565C0"

    # สร้างแถวประวัติ
    row_contents = []
    for i, rec in enumerate(records):
        created_at_raw, weight_val, height_val, bmi_val, goal_val = rec
        # แปลงวันที่
        try:
            from datetime import datetime as dt
            dt_obj = dt.fromisoformat(str(created_at_raw))
            date_str = dt_obj.strftime("%d/%m/%y %H:%M")
        except Exception:
            date_str = str(created_at_raw)[:16]

        bmi_float = float(bmi_val) if bmi_val else 22.0
        level, icon = bmi_level_info(bmi_float)
        col = color_map.get(level, "#666666")
        label = "ล่าสุด" if i == 0 else f"#{i+1}"

        row_contents.append({
            "type": "box",
            "layout": "horizontal",
            "paddingAll": "6px",
            "backgroundColor": "#F5F5F5" if i % 2 == 0 else "#FFFFFF",
            "contents": [
                {"type": "text", "text": label, "size": "xxs", "color": "#999999", "flex": 2, "align": "center"},
                {"type": "text", "text": date_str, "size": "xxs", "color": "#555555", "flex": 4},
                {"type": "text", "text": f"{float(weight_val):.1f}kg" if weight_val else "-", "size": "xxs", "color": "#333333", "flex": 2, "align": "center"},
                {"type": "text", "text": f"{bmi_float:.1f}", "size": "xxs", "weight": "bold", "color": col, "flex": 2, "align": "center"},
                {"type": "text", "text": f"{icon}", "size": "xs", "color": col, "flex": 2, "align": "center"}
            ]
        })

    # header แถว
    header_row = {
        "type": "box",
        "layout": "horizontal",
        "paddingAll": "6px",
        "backgroundColor": "#E8EAF6",
        "contents": [
            {"type": "text", "text": "ครั้งที่", "size": "xxs", "color": "#3949AB", "weight": "bold", "flex": 2, "align": "center"},
            {"type": "text", "text": "วันที่/เวลา", "size": "xxs", "color": "#3949AB", "weight": "bold", "flex": 4},
            {"type": "text", "text": "น้ำหนัก", "size": "xxs", "color": "#3949AB", "weight": "bold", "flex": 2, "align": "center"},
            {"type": "text", "text": "BMI", "size": "xxs", "color": "#3949AB", "weight": "bold", "flex": 2, "align": "center"},
            {"type": "text", "text": "ระดับ", "size": "xxs", "color": "#3949AB", "weight": "bold", "flex": 2, "align": "center"}
        ]
    }

    flex_json = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1A237E",
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "text",
                    "text": "📈 ประวัติพัฒนาการ BMI",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "lg"
                },
                {
                    "type": "text",
                    "text": f"บันทึกล่าสุด {len(records)} ครั้ง",
                    "color": "#C5CAE9",
                    "size": "xs",
                    "margin": "xs"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "none",
            "paddingAll": "0px",
            "contents": [
                header_row,
                *row_contents,
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "paddingAll": "10px",
                    "backgroundColor": "#F3F4FF",
                    "contents": [
                        {
                            "type": "text",
                            "text": trend_text,
                            "size": "xs",
                            "weight": "bold",
                            "color": trend_color,
                            "wrap": True
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#1A237E",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "📊 อัปเดตข้อมูลใหม่",
                        "text": "ชาย 25 70 175 ลดน้ำหนัก ปานกลาง"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "🍽️ เมนูอาหาร",
                        "text": "แนะนำอาหารหน่อย"
                    }
                }
            ]
        }
    }

    return {
        "type": "flex",
        "alt_text": f"📈 ประวัติ BMI ({len(records)} ครั้ง)",
        "flex_contents": flex_json
    }


# =========================================================
# Action แสดงประวัติพัฒนาการ BMI ย้อนหลัง
# =========================================================
class ActionShowBMIHistory(Action):

    def name(self) -> Text:
        return "action_show_bmi_history"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        user_id = tracker.sender_id

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # ดึงประวัติล่าสุด 5 ครั้ง
            cursor.execute(
                """
                SELECT created_at, weight, height, bmi, goal
                FROM bmi_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 5
                """,
                (user_id,)
            )
            records = cursor.fetchall()
            conn.close()

            if not records:
                dispatcher.utter_message(
                    text=(
                        "📭 ยังไม่มีประวัติการบันทึก BMI ของคุณในระบบค่ะ\n"
                        "ลองคำนวณ BMI ครั้งแรกได้เลยนะคะ!\n\n"
                        "📝 ตัวอย่าง: ชาย 25 70 175 ลดน้ำหนัก ปานกลาง"
                    )
                )
                return []

            # คำนวณ summary
            latest = records[0]
            latest_bmi = float(latest[3]) if latest[3] else 0.0
            if latest_bmi < 18.5:
                latest_level = "ผอม"
            elif latest_bmi < 23:
                latest_level = "ปกติ"
            elif latest_bmi < 25:
                latest_level = "น้ำหนักเกิน"
            else:
                latest_level = "อ้วน"

            summary_text = (
                f"📈 ประวัติ BMI ของคุณ ({len(records)} ครั้งล่าสุด)\n"
                f"─────────────────────\n"
                f"🔵 BMI ล่าสุด: {latest_bmi:.2f} ({latest_level})\n"
                f"⚖️ น้ำหนักล่าสุด: {float(latest[1]):.1f} kg\n"
            )

            if len(records) >= 2:
                first_bmi = float(records[-1][3]) if records[-1][3] else latest_bmi
                diff = round(latest_bmi - first_bmi, 2)
                if diff < 0:
                    summary_text += f"✅ BMI ลดลง {abs(diff):.2f} จากครั้งแรกที่บันทึก — เยี่ยมมากค่ะ!"
                elif diff > 0:
                    summary_text += f"⚠️ BMI เพิ่มขึ้น {diff:.2f} จากครั้งแรกที่บันทึก"
                else:
                    summary_text += "➡️ BMI ไม่เปลี่ยนแปลง — รักษาระดับได้ดีค่ะ"

            flex_payload = build_bmi_history_flex_card(records)

            dispatcher.utter_message(
                text=summary_text,
                custom=flex_payload
            )

        except Exception as e:
            print(f"Error in ActionShowBMIHistory: {e}")
            dispatcher.utter_message(
                text="⚠️ เกิดข้อผิดพลาดในการดึงประวัติ BMI กรุณาลองใหม่อีกครั้งค่ะ"
            )

        return []


# =========================================================
# Action Fallback: ตอบโต้เมื่อบอทไม่เข้าใจคำถาม
# =========================================================
class ActionCustomFallback(Action):

    def name(self) -> Text:
        return "action_custom_fallback"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get("text", "")

        flex_json = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#E65100",
                "paddingAll": "15px",
                "contents": [
                    {
                        "type": "text",
                        "text": "🤔 ไม่เข้าใจคำถามนี้ค่ะ",
                        "weight": "bold",
                        "color": "#FFFFFF",
                        "size": "lg"
                    },
                    {
                        "type": "text",
                        "text": "ลองเลือกจากเมนูที่ฉันทำได้ด้านล่างนะคะ",
                        "color": "#FFE0B2",
                        "size": "xs",
                        "margin": "xs",
                        "wrap": True
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "text",
                        "text": "💡 สิ่งที่ฉันช่วยได้:",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#333333"
                    },
                    {"type": "separator"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "xs",
                        "contents": [
                            {
                                "type": "box", "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": "📊", "size": "sm", "flex": 1},
                                    {"type": "box", "layout": "vertical", "flex": 9, "contents": [
                                        {"type": "text", "text": "คำนวณ BMI, BMR, TDEE", "size": "xs", "weight": "bold", "color": "#333333"},
                                        {"type": "text", "text": "พิมพ์: ชาย 25 70 175 ลดน้ำหนัก ปานกลาง", "size": "xxs", "color": "#999999", "wrap": True}
                                    ]}
                                ]
                            },
                            {"type": "separator"},
                            {
                                "type": "box", "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": "🍽️", "size": "sm", "flex": 1},
                                    {"type": "box", "layout": "vertical", "flex": 9, "contents": [
                                        {"type": "text", "text": "แนะนำเมนูอาหารตาม BMI", "size": "xs", "weight": "bold", "color": "#333333"},
                                        {"type": "text", "text": "พิมพ์: แนะนำอาหารหน่อย", "size": "xxs", "color": "#999999"}
                                    ]}
                                ]
                            },
                            {"type": "separator"},
                            {
                                "type": "box", "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": "🏋️", "size": "sm", "flex": 1},
                                    {"type": "box", "layout": "vertical", "flex": 9, "contents": [
                                        {"type": "text", "text": "ตารางออกกำลังกาย", "size": "xs", "weight": "bold", "color": "#333333"},
                                        {"type": "text", "text": "พิมพ์: แนะนำการออกกำลังกาย", "size": "xxs", "color": "#999999"}
                                    ]}
                                ]
                            },
                            {"type": "separator"},
                            {
                                "type": "box", "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": "📈", "size": "sm", "flex": 1},
                                    {"type": "box", "layout": "vertical", "flex": 9, "contents": [
                                        {"type": "text", "text": "ดูประวัติพัฒนาการ BMI", "size": "xs", "weight": "bold", "color": "#333333"},
                                        {"type": "text", "text": "พิมพ์: ดูประวัติ BMI หน่อย", "size": "xxs", "color": "#999999"}
                                    ]}
                                ]
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1565C0",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "📊 คำนวณ BMI",
                            "text": "ชาย 25 70 175 ลดน้ำหนัก ปานกลาง"
                        }
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "style": "secondary",
                                "height": "sm",
                                "flex": 1,
                                "action": {
                                    "type": "message",
                                    "label": "🍽️ อาหาร",
                                    "text": "แนะนำอาหารหน่อย"
                                }
                            },
                            {
                                "type": "button",
                                "style": "secondary",
                                "height": "sm",
                                "flex": 1,
                                "action": {
                                    "type": "message",
                                    "label": "🏋️ ออกกำลังกาย",
                                    "text": "แนะนำการออกกำลังกายหน่อย"
                                }
                            },
                            {
                                "type": "button",
                                "style": "secondary",
                                "height": "sm",
                                "flex": 1,
                                "action": {
                                    "type": "message",
                                    "label": "📈 ประวัติ",
                                    "text": "ดูประวัติ BMI หน่อย"
                                }
                            }
                        ]
                    }
                ]
            }
        }

        flex_payload = {
            "type": "flex",
            "alt_text": "🤔 ไม่เข้าใจคำถาม — เลือกจากเมนูด้านล่างได้เลยค่ะ",
            "flex_contents": flex_json
        }

        dispatcher.utter_message(
            text=(
                f"ขออภัยค่ะ ฉันยังไม่เข้าใจ: \"{user_message}\" 😅\n"
                "ลองดูสิ่งที่ฉันช่วยได้จากเมนูด้านล่างนะคะ"
            ),
            custom=flex_payload
        )

        return []
