# 📋 เอกสารสรุปโค้ดและสถาปัตยกรรมระบบ (LINE Health Chatbot with Rasa)

> **วัตถุประสงค์ของเอกสาร:** เอกสารฉบับนี้จัดทำขึ้นเพื่อเป็นข้อมูลอ้างอิงทางเทคนิค (Technical Reference Documentation) สำหรับนำไปใช้งานต่อบน Gemini หรือ AI ตัวอื่นๆ เพื่อให้เข้าใจโครงสร้าง สถาปัตยกรรม การทำงานของโค้ดทุกไฟล์ ฐานข้อมูล และ API ทั้งหมดของระบบ

---

## 📑 สารบัญ (Table of Contents)
1. [ภาพรวมของระบบ (System Overview)](#1-ภาพรวมของระบบ-system-overview)
2. [สถาปัตยกรรมและการไหลของข้อมูล (System Architecture & Data Flow)](#2-สถาปัตยกรรมและการไหลของข้อมูล-system-architecture--data-flow)
3. [โครงสร้างไดเรกทอรีและไฟล์ทั้งหมด (Project Structure)](#3-โครงสร้างไดเรกทอรีและไฟล์ทั้งหมด-project-structure)
4. [คำอธิบายการทำงานของแต่ละไฟล์ (Detailed File Breakdown)](#4-คำอธิบายการทำงานของแต่ละไฟล์-detailed-file-breakdown)
   - [run.py & run.bat (Launcher)](#41-runpy--runbat)
   - [webhook.py (LINE Webhook Bridge)](#42-webhookpy)
   - [config.yml (Rasa Pipeline & Policies)](#43-configyml)
   - [domain.yml (Intents, Entities, Slots, Responses)](#44-domainyml)
   - [data/nlu.yml (NLU Training Data)](#45-datanluyml)
   - [data/rules.yml (Dialogue Rules)](#46-datarulesyml)
   - [actions/actions.py (Custom Action Server & SQLite)](#47-actionsactionspy)
5. [ฐานข้อมูลและการจัดเก็บ (Database Schema)](#5-ฐานข้อมูลและการจัดเก็บ-database-schema)
6. [สูตรการคำนวณสุขภาพ (Health Calculation Formulas)](#6-สูตรการคำนวณสุขภาพ-health-calculation-formulas)
7. [ระบบ LINE Flex Message & Quick Reply](#7-ระบบ-line-flex-message--quick-reply)
8. [ขั้นตอนการรันระบบและการทดสอบ (How to Run & Test)](#8-ขั้นตอนการรันระบบและการทดสอบ-how-to-run--test)
9. [ฟีเจอร์และจุดปรับปรุงล่าสุด (Recent Updates & Features)](#9-ฟีเจอร์และจุดปรับปรุงล่าสุด-recent-updates--features)

---

## 1. ภาพรวมของระบบ (System Overview)

ระบบนี้เป็น **AI Health & Nutrition Assistant Chatbot** ใช้งานผ่านแอปพลิเคชัน **LINE** พัฒนาขึ้นโดยใช้เฟรมเวิร์ก **Rasa Open Source (เวอร์ชัน 3.x)** ทำงานร่วมกับ **Python Flask**, **LINE Messaging API**, และฐานข้อมูล **SQLite**

### ความสามารถหลักของบอท:
1. **คำนวณดัชนีมวลกาย (BMI Calculation):** ประเมินระดับความสมส่วนของร่างกาย (ผอม, ปกติ, น้ำหนักเกิน, อ้วน)
2. **คำนวณค่าพลังงานและสารอาหารแบบครบวงจร (Full Health Metrics):** 
   - คำนวณ BMR (Basal Metabolic Rate) ด้วยสูตร Mifflin-St Jeor
   - คำนวณ TDEE (Total Daily Energy Expenditure) ตามระดับกิจกรรม
   - คำนวณพลังงานเป้าหมายตาม Goal (ลดน้ำหนัก / รักษาน้ำหนัก / เพิ่มกล้ามเนื้อ)
   - คำนวณสารอาหารหลัก Macros (โปรตีน, คาร์โบไฮเดรต, ไขมัน)
   - คำนวณปริมาณน้ำดื่มที่เหมาะสมต่อวัน (ลิตร และ แก้ว)
3. **แนะนำเมนูอาหารสุขภาพ (Smart Food Recommendation):** สุ่มเมนูอาหารตามระดับ BMI ของผู้ใช้ พร้อมรูปภาพอาหารสวยงามตรงเมนู แคลอรี และคำอธิบาย โดยระบบมีกลไกป้องกันการแนะนำเมนูซ้ำติดกัน
4. **แนะนำตารางออกกำลังกาย (Personalized Workout Plan):** วางแผนการออกกำลังกาย 3 รูปแบบ (Cardio, Strength, Flexibility/Rest) ตามเป้าหมายและค่า BMI ในรูปแบบ Carousel Flex Message
5. **บันทึกและดูประวัติ BMI ย้อนหลัง (BMI History & Trend):** เก็บข้อมูลลง SQLite และแสดงประวัติ 5 ครั้งล่าสุดในรูปแบบตาราง พร้อมวิเคราะห์แนวโน้ม (ลดลง/คงที่/เพิ่มขึ้น)
6. **ระบบรองรับกรณีไม่เข้าใจคำถาม (Custom Fallback Handling):** เมื่อคะแนนความมั่นใจต่ำ (Confidence < 0.4) จะแสดง Flex Card แนะนำเมนูและวิธีการพิมพ์อย่างถูกต้อง

---

## 2. สถาปัตยกรรมและการไหลของข้อมูล (System Architecture & Data Flow)

```
[ ผู้ใช้งาน LINE ]
       │
       ▼ (HTTPS Webhook)
[ LINE Platform (Messaging API) ]
       │
       ▼ (Forward via Ngrok Tunnel: https://xxxx.ngrok-free.app/callback)
[ webhook.py (Flask Server: Port 8000) ]
       │
       ▼ (HTTP POST: http://localhost:5005/webhooks/rest/webhook)
[ Rasa Core & NLU Server (Port 5005) ]
       │  ├─ ตัดคำ / ดึง Intent & Entities (DIETClassifier)
       │  └─ ตรวจสอบ Policy (Rules / Memoization / TED)
       │
       ▼ (HTTP POST Action Request: http://localhost:5055/webhook)
[ Rasa Action Server (actions/actions.py: Port 5055) ]
       │
       ├─► [ SQLite Database: actions/bmi.db ] (bmi_history & food_recommendations)
       │
       ▼ (Return Action Response + Custom Flex Payload)
[ webhook.py ]
       │
       ▼ (reply_message: FlexSendMessage / TextSendMessage + QuickReply)
[ LINE Platform ] ──► [ หน้าจอ LINE ของผู้ใช้ ]
```

---

## 3. โครงสร้างไดเรกทอรีและไฟล์ทั้งหมด (Project Structure)

```text
new project/
├── actions/
│   ├── __init__.py
│   ├── actions.py             # โค้ด Custom Actions ทั้งหมด 6 คลาส + ฟังก์ชันสร้าง Flex Card
│   └── bmi.db                 # ฐานข้อมูล SQLite เก็บประวัติ BMI และเมนูอาหาร
├── data/
│   ├── nlu.yml                # ข้อมูลฝึกสอน Intent, Entity, และประโยคตัวอย่างภาษาไทย
│   ├── rules.yml              # กฎการตอบกลับ (Intent -> Action mapping)
│   └── stories.yml            # บทสนทนาจำลอง (Dialogue training stories)
├── models/                    # โฟลเดอร์เก็บไฟล์โมเดล Rasa ที่ train แล้ว (.tar.gz)
├── rasa_env/                  # Virtual Environment (Python 3.10 + Rasa 3.x)
├── config.yml                 # การตั้งค่า NLU Pipeline และ Core Policies
├── credentials.yml            # การเปิดใช้งานช่องทางติดต่อ (REST Channel)
├── domain.yml                 # ทะเบียนระบุ Intent, Slot, Response, และ Action
├── endpoints.yml              # URL สำหรับเชื่อมต่อ Action Server (http://localhost:5055/webhook)
├── run.py                     # Script ตัวจัดการรันทุก Service พร้อมกัน พร้อมระบบมอนิเตอร์และสี ANSI
├── run.bat                    # Batch file สำหรับดับเบิลคลิกเริ่มระบบได้ทันที
├── webhook.py                 # Flask Server เชื่อมโยง LINE Bot API กับ Rasa
└── PROJECT_SUMMARY.md         # เอกสารสรุปโค้ดและคู่มือระบบ (ไฟล์นี้)
```

---

## 4. คำอธิบายการทำงานของแต่ละไฟล์ (Detailed File Breakdown)

### 4.1 `run.py` & `run.bat`
- **หน้าที่:** รันเซอร์วิสทั้งหมดของระบบพร้อมกันใน Command Line เดียว โดยไม่ต้องเปิดหลายหน้าต่าง
- **เซอร์วิสที่สั่งรัน:**
  1. `Rasa Action Server`: `rasa_env\Scripts\rasa.exe run actions` (Port 5055)
  2. `Rasa Core Server`: `rasa_env\Scripts\rasa.exe run --enable-api` (Port 5055)
  3. `Webhook Server`: `rasa_env\Scripts\python.exe webhook.py` (Port 8000)
  4. `Ngrok Tunnel` (Optional): `ngrok http 8000` (เปิด Tunnel สาธารณะเข้า LINE)
- **ฟีเจอร์เด่นในโค้ด:**
  - แยกสี Log แต่ละ Service ด้วย ANSI Color Codes (Cyan, Green, Magenta, Yellow)
  - มีฟังก์ชันดักจับ `Ctrl+C` (Signal Handler) และเรียกคำสั่ง `taskkill /F /T /PID` เพื่อปิด Process tree บน Windows อย่างหมดจด ป้องกัน Port ค้าง

---

### 4.2 `webhook.py`
- **หน้าที่:** ตัวกลาง (Bridge/Proxy) ระหว่าง LINE Messaging API กับ Rasa Core Server
- **เทคโนโลยี:** Flask, LineBotApi, WebhookHandler (`line-bot-sdk`)
- **การประมวลผลข้อความ:**
  1. รับ Request POST จาก LINE ที่ Endpoint `/callback` และตรวจยืนยันลายเซ็นดิจิทัล `X-Line-Signature`
  2. ดึง `user_id` และข้อความ `user_message` แล้วส่งต่อไปยัง Rasa ผ่าน REST endpoint: `http://localhost:5005/webhooks/rest/webhook`
  3. แปลง Response จาก Rasa:
     - หากได้รับ `custom` payload ที่มี `"type": "flex"` จะแปลงเป็น `FlexSendMessage`
     - หากได้รับข้อความทั่วไป จะแปลงเป็น `TextSendMessage`
  4. ติดตั้งปุ่ม **Quick Reply** (5 ปุ่มด่วน: แนะนำอาหาร, ออกกำลังกาย, ประวัติ BMI, ข้อมูล BMR/TDEE, คำนวณสุขภาพ)
  5. รองรับข้อความยาวเกิน 5 ข้อความ โดยชุดแรกส่งผ่าน `reply_message` และส่วนที่เหลือส่งด้วย `push_message`

---

### 4.3 `config.yml`
- **หน้าที่:** กำหนดค่าการเรียนรู้ภาษาธรรมชาติ (NLU Pipeline) และนโยบายตัดสินใจ (Dialogue Policies)
- **NLU Pipeline:**
  - `WhitespaceTokenizer`: ตัดคำพื้นฐาน
  - `RegexFeaturizer`: สกัดคุณลักษณะจากรูปแบบตัวเลข/คำ
  - `LexicalSyntacticFeaturizer`: สกัดลักษณะไวยากรณ์
  - `CountVectorsFeaturizer` (Word level & Char N-gram 1-4): แปลงข้อความเป็นเวกเตอร์ความถี่คำ
  - `DIETClassifier` (100 Epochs): โมเดล Neural Network ทำนาย Intent และสกัด Entity พร้อมกัน
  - `FallbackClassifier` (`threshold: 0.4`): หากคะแนนความมั่นใจต่ำกว่า 40% จะเปลี่ยนเป็น Intent `nlu_fallback` อัตโนมัติ
- **Core Policies:**
  - `RulePolicy`: จัดการ Rule-based conversations และ Core fallback
  - `MemoizationPolicy` & `TEDPolicy`: พยากรณ์ลำดับ Action ตามประวัติการสนทนา

---

### 4.4 `domain.yml`
- **หน้าที่:** คลังข้อมูลส่วนกลางของ Rasa รวบรวมองค์ประกอบทั้งหมดของบอท
- **Intents (11 Intents):**
  `greet`, `inform_profile`, `inform_health_profile`, `ask_bmi`, `ask_bmr_tdee`, `ask_bot`, `goodbye`, `ask_food_recommendation`, `ask_workout_recommendation`, `ask_bmi_history`, `nlu_fallback`
- **Entities (6 Entities):**
  `weight`, `height`, `goal`, `activity_level`, `age`, `gender`
- **Slots (7 Slots):**
  `weight` (float), `height` (float), `goal` (text), `activity_level` (text), `age` (float), `gender` (text), `last_food_menu` (text)
- **Actions (7 Actions):**
  `action_calculate_bmi`, `action_calculate_health_metrics`, `action_recommend_food`, `action_recommend_workout`, `action_show_bmi_history`, `action_custom_fallback`, `action_default_fallback`

---

### 4.5 `data/nlu.yml`
- **หน้าที่:** ข้อมูลสำหรับฝึกสอน NLU มีประโยคตัวอย่างภาษาไทยและติดแท็ก Entity ไว้อย่างละเอียด เช่น:
  - `inform_health_profile`: `[ชาย](gender) [25](age) [70](weight) [175](height) [ลดน้ำหนัก](goal) [ปานกลาง](activity_level)`
  - `ask_food_recommendation`: `แนะนำอาหารหน่อย`, `กินอะไรดี`, `เมนูสุขภาพวันนี้`
  - `ask_workout_recommendation`: `ตารางออกกำลังกาย`, `ออกกำลังกายยังไงดี`
  - `ask_bmi_history`: `ดูประวัติ bmi`, `ประวัติการคำนวณ`, `บันทึก bmi ย้อนหลัง`

---

### 4.6 `data/rules.yml`
- **หน้าที่:** แมปคู่ Intent ไปสู่ Action โดยตรงแบบ Deterministic (ทำงานทันทีไม่ต้องเดา):
  - `greet` ➔ `utter_greet` + `utter_ask_profile`
  - `inform_profile` ➔ `action_calculate_bmi`
  - `inform_health_profile` ➔ `action_calculate_health_metrics`
  - `ask_food_recommendation` ➔ `action_recommend_food`
  - `ask_workout_recommendation` ➔ `action_recommend_workout`
  - `ask_bmi_history` ➔ `action_show_bmi_history`
  - `nlu_fallback` ➔ `action_custom_fallback`

---

### 4.7 `actions/actions.py`
ไฟล์สำคัญที่สุด มีความยาวกว่า 1,580 บรรทัด ประกอบด้วย 6 Action Classes และ 4 Flex Message Generator Functions:

#### ฟังก์ชันช่วยสร้าง Flex Message (LINE Flex UI Builders):
1. **`build_health_flex_card(...)`**: สร้างการ์ดผลลัพธ์สุขภาพครบวงจร แสดง BMI, BMR, TDEE, แคลอรีเป้าหมาย, น้ำดื่ม (ลิตร+แก้ว), และแถบสารอาหารโปรตีน/คาร์บ/ไขมัน
2. **`build_food_flex_card(...)`**: สร้างการ์ดเมนูอาหารพร้อมภาพถ่าย Unsplash ความคมชัดสูง, Badge บอกระดับ BMI, แคลอรี, และปุ่มกดเปลี่ยนเมนู
3. **`build_workout_carousel_flex(...)`**: สร้างการ์ดสไลด์ (Carousel) แนะนำการออกกำลังกาย 3 ด้านตามเป้าหมาย (Cardio, Strength, Flexibility)
4. **`build_bmi_history_flex_card(records)`**: สร้างการ์ดตารางประวัติ 5 แถว พร้อมคำนวณส่วนต่างและแนวโน้มสุขภาพ

#### คลาส Action ทั้ง 6 คลาส:
1. **`ActionCalculateBMI`**:
   - คำนวณ BMI จากน้ำหนัก/ส่วนสูง
   - บันทึกข้อมูลลงตาราง `bmi_history`
   - ส่งผลลัพธ์ข้อความและ Flex Message สรุปผล
2. **`ActionCalculateHealthMetrics`**:
   - รับพารามิเตอร์ครบ: เพศ, อายุ, น้ำหนัก, ส่วนสูง, เป้าหมาย, ระดับกิจกรรม
   - คำนวณ BMR (Mifflin-St Jeor), TDEE, Target Calories, Macros, Water
   - อัปเดตบันทึกลงตาราง `bmi_history`
   - ส่งผลลัพธ์ด้วย `build_health_flex_card`
3. **`ActionRecommendFood`**:
   - อ่านระดับ BMI ล่าสุดของผู้ใช้
   - สุ่มค้นหาเมนูอาหารจากตาราง `food_recommendations` ในหมวดนั้น
   - ตรวจสอบ `last_food_menu` เพื่อไม่ให้สุ่มได้เมนูเดิมซ้ำติดกัน
   - ส่งผลลัพธ์ด้วย `build_food_flex_card`
4. **`ActionRecommendWorkout`**:
   - ปรับแผนออกกำลังกายตาม Goal และระดับ BMI
   - ส่งผลลัพธ์เป็น Carousel 3 การ์ด
5. **`ActionShowBMIHistory`**:
   - ดึงข้อมูล 5 รายการล่าสุดจาก `bmi_history` ตาม `user_id` ของผู้ใช้ LINE
   - คำนวณผลต่าง BMI ระหว่างครั้งแรกและล่าสุด
   - ส่งกลับเป็นตาราง Flex Card
6. **`ActionCustomFallback`**:
   - ทำงานเมื่อคะแนน NLU ต่ำกว่าเกณฑ์
   - ส่งการ์ดสีส้มระบุปัญหาอย่างเป็นมิตร พร้อมไกด์ไลน์วิธีการพิมพ์และปุ่มกดด่วน

---

## 5. ฐานข้อมูลและการจัดเก็บ (Database Schema)

ระบบใช้ฐานข้อมูล **SQLite** ไฟล์ตั้งอยู่ที่ `actions/bmi.db` มี 2 ตารางหลัก:

### 5.1 ตาราง `bmi_history` (ประวัติผู้ใช้งาน)
| ชื่อคอลัมน์ | ประเภทข้อมูล | คำอธิบาย |
|:---|:---|:---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | รหัสแถว |
| `user_id` | TEXT | LINE User ID ของผู้ใช้ |
| `weight` | REAL | น้ำหนัก (กก.) |
| `height` | REAL | ส่วนสูง (ซม.) |
| `age` | INTEGER | อายุ (ปี) |
| `gender` | TEXT | เพศ ("ชาย" หรือ "หญิง") |
| `bmi` | REAL | ค่าดัชนีมวลกาย |
| `bmr` | REAL | อัตราการเผาผลาญพื้นฐาน (kcal) |
| `tdee` | REAL | พลังงานที่ใช้ต่อวันรวมกิจกรรม (kcal) |
| `goal` | TEXT | เป้าหมาย (เช่น ลดน้ำหนัก, เพิ่มกล้ามเนื้อ) |
| `activity` | TEXT | ระดับกิจกรรม (นั่งทำงาน, เบา, ปานกลาง, หนัก) |
| `created_at` | TEXT | วันที่และเวลาที่บันทึก (YYYY-MM-DD HH:MM:SS) |

### 5.2 ตาราง `food_recommendations` (เมนูอาหารแนะนำ)
มีข้อมูลตั้งต้น 16 เมนู (4 เมนูต่อหมวด BMI):
| ชื่อคอลัมน์ | ประเภทข้อมูล | คำอธิบาย |
|:---|:---|:---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | รหัสเมนู |
| `bmi_category` | TEXT | หมวด BMI: `'ผอม'`, `'ปกติ'`, `'น้ำหนักเกิน'`, `'อ้วน'` |
| `menu_name` | TEXT | ชื่อเมนูอาหารไทย |
| `calories` | INTEGER | ปริมาณแคลอรีโดยประมาณ (kcal) |
| `description` | TEXT | ประโยชน์และสารอาหารสำคัญ |
| `image_url` | TEXT | ลิงก์รูปภาพอาหารความคมชัดสูงจาก Unsplash |

---

## 6. สูตรการคำนวณสุขภาพ (Health Calculation Formulas)

### 6.1 ค่าดัชนีมวลกาย (BMI - Body Mass Index)
$$\text{BMI} = \frac{\text{น้ำหนัก (kg)}}{(\text{ส่วนสูง (m)})^2}$$
**เกณฑ์การประเมิน (มาตรฐานเอเชีย):**
- $\text{BMI} < 18.5$ : ผอม / น้ำหนักต่ำกว่าเกณฑ์
- $18.5 \le \text{BMI} < 23.0$ : ปกติ / สุขภาพดี
- $23.0 \le \text{BMI} < 25.0$ : น้ำหนักเกิน
- $\text{BMI} \ge 25.0$ : อ้วน

### 6.2 ค่าการเผาผลาญพื้นฐาน (BMR - Basal Metabolic Rate)
ใช้สูตร **Mifflin-St Jeor Equation** (แม่นยำที่สุดตามหลักโภชนาการ):
- **เพศชาย:**
  $$\text{BMR} = 10 \times \text{weight (kg)} + 6.25 \times \text{height (cm)} - 5 \times \text{age (yrs)} + 5$$
- **เพศหญิง:**
  $$\text{BMR} = 10 \times \text{weight (kg)} + 6.25 \times \text{height (cm)} - 5 \times \text{age (yrs)} - 161$$

### 6.3 พลังงานที่ใช้ในชีวิตประจำวัน (TDEE - Total Daily Energy Expenditure)
$$\text{TDEE} = \text{BMR} \times \text{Activity Multiplier}$$
- นั่งทำงานอยู่กับที่ / ไม่ออกกำลังกาย: $\times 1.2$
- กิจกรรมเบา (ออกกำลังกาย 1-3 วัน/สัปดาห์): $\times 1.375$
- กิจกรรมปานกลาง (ออกกำลังกาย 3-5 วัน/สัปดาห์): $\times 1.55$
- กิจกรรมหนัก (ออกกำลังกาย 6-7 วัน/สัปดาห์): $\times 1.725$

### 6.4 พลังงานเป้าหมายและสัดส่วนสารอาหาร (Macros Split)
- **ลดน้ำหนัก (Fat Loss):** Target Calorie $= \text{TDEE} - 500 \text{ kcal}$
  - โปรตีน: 30% | คาร์โบไฮเดรต: 40% | ไขมัน: 30%
- **เพิ่มกล้ามเนื้อ (Muscle Gain):** Target Calorie $= \text{TDEE} + 300 \text{ kcal}$
  - โปรตีน: 30% | คาร์โบไฮเดรต: 50% | ไขมัน: 20%
- **รักษาสุขภาพ (Maintenance):** Target Calorie $= \text{TDEE}$
  - โปรตีน: 25% | คาร์โบไฮเดรต: 50% | ไขมัน: 25%

### 6.5 ปริมาณน้ำดื่มต่อวัน (Daily Water Requirement)
$$\text{Water (Litres)} = \frac{\text{weight (kg)} \times 33}{1000}$$
$$\text{จำนวนแก้ว (Glasses)} = \text{round}\left(\frac{\text{Water (Litres)} \times 1000}{250}\right)$$

---

## 7. ระบบ LINE Flex Message & Quick Reply

ทุกคำตอบจากบอทถูกออกแบบให้เป็น **Rich UI** เพื่อประสบการณ์ผู้ใช้งานระดับพรีเมียม:
- **Flex Bubble Cards:** ใช้สีโทนสุขภาพ (Navy `#1A237E`, Cyan `#0097A7`, Orange `#E65100`, Emerald `#2E7D32`)
- **Interactive Buttons:** ทุกการ์ดมีปุ่ม Call-to-Action ด้านล่าง เช่น "🍽️ แนะนำอาหาร", "🏋️‍♂️ ตารางออกกำลังกาย", "📈 ดูประวัติ BMI"
- **Persistent Quick Reply:** ติดตั้ง 5 ปุ่มด่วนท้ายข้อความเสมอ เพื่อให้ผู้ใช้กดคุยต่อได้ง่ายโดยไม่ต้องจำคำสั่ง

---

## 8. ขั้นตอนการรันระบบและการทดสอบ (How to Run & Test)

### 8.1 การเริ่มระบบทั้งหมด
เปิด Terminal แล้วรันคำสั่ง:
```bash
python run.py
```
หรือดับเบิลคลิกที่ไฟล์ `run.bat`

### 8.2 การตั้งค่า Webhook บน LINE Developers Console
1. นำ URL สาธารณะที่ได้จาก Ngrok เช่น:
   `https://xxxx-xx-xx.ngrok-free.app/callback`
2. นำไปกรอกในเมนู **Messaging API** > **Webhook URL** บน LINE Developers Console
3. เปิดสวิตช์ **Use Webhook** ให้เป็น `ON`
4. ปิด Auto-reply Messages ของระบบ LINE Official Account เพื่อไม่ให้ตอบซ้ำซ้อนกับบอท

### 8.3 การเทรนโมเดลใหม่เมื่อมีการแก้ไขข้อมูล
เมื่อแก้ไขไฟล์ `data/nlu.yml`, `data/rules.yml` หรือ `domain.yml` ให้รันคำสั่ง:
```bash
.\rasa_env\Scripts\rasa.exe train
```

---

## 9. ฟีเจอร์และจุดปรับปรุงล่าสุด (Recent Updates & Features)

1. **อัปเกรดรูปภาพเมนูอาหารทั้งหมด (Food Images Overhaul):**
   - แก้ไขลิงก์รูปภาพเมนูอาหารทั้ง 16 รายการในฐานข้อมูล SQLite ให้มีรูปภาพตรงตามชนิดอาหารแต่ละจานอย่างแม่นยำผ่าน Unsplash Photos (เช่น สเต๊กปลาแซลมอน, สลัดอกไก่, ต้มยำกุ้ง, ไข่ตุ๋น ฯลฯ)
   - มีระบบ Auto-Migration ใน `db_init()` อัปเดตลิงก์รูปภาพในฐานข้อมูลเดิมทุกครั้งที่เซิร์ฟเวอร์เปิดทำงาน
2. **ระบบประวัติและการเปรียบเทียบพัฒนาการ BMI (BMI History):**
   - เพิ่ม Intent `ask_bmi_history`
   - เพิ่ม Action `action_show_bmi_history`
   - แสดงผลประวัติ 5 ครั้งล่าสุดในตาราง Flex Card พร้อมบอกผลต่างเชิงบวก/ลบ
3. **ระบบ Custom Fallback ป้องกันการตอบผิดพลาด:**
   - ติดตั้ง `FallbackClassifier` ความไวที่ Threshold 0.4
   - เพิ่ม Action `action_custom_fallback` ส่งการ์ดคู่มือการใช้งานเมื่อผู้ใช้พิมพ์คำสั่งที่บอทไม่คุ้นเคย
4. **ปุ่ม Quick Reply ครอบคลุมทุกฟีเจอร์หลัก:**
   - เพิ่มปุ่ม "📈 ประวัติ BMI" ลงใน Quick Reply ของ Webhook และ Flex Cards ทุกชุด

---

*(จัดทำโดย Antigravity IDE Assistant สำหรับใช้เป็นเอกสารอ้างอิงและพัฒนาต่อยอด)*
