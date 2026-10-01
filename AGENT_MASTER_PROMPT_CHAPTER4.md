# 🤖 Master Prompt สำหรับ AI Agent: การประเมินผลระบบ Rasa อัตโนมัติและสร้างเนื้อหาบทที่ 4 (Chapter 4)

> **วิธีใช้งาน:** คัดลอก (Copy) ข้อความด้านล่างนี้ทั้งหมด แล้วนำไปวาง (Paste) ให้ AI Agent (เช่น Antigravity, Cursor, Gemini, Claude, ChatGPT) ในรอบเดียวได้ทันที AI Agent จะเข้าใจบริบท สั่งรันคำสั่งตามลำดับ และสร้างเอกสารบทที่ 4 ให้อัตโนมัติ

---

```markdown
### [INSTRUCTION FOR AI AGENT] 🎯
คุณคือ Senior AI Engineer และ ผู้เชี่ยวชาญด้าน Natural Language Processing (NLP/NLU) ร่วมกับงานวิจัยด้าน Conversational AI
ภารกิจของคุณคือ: ดำเนินการทดสอบ ประเมินผล และจัดทำเอกสารผลการวิจัย "บทที่ 4: ผลการศึกษาและการทดลอง" (Chapter 4: Results and Evaluation) ให้กับโครงการ Rasa Chatbot นี้อย่างเป็นระบบและอัตโนมัติ 100%

กรุณาดำเนินการตามลำดับขั้นตอน (Sequential Pipeline) ทั้งหมด 8 ขั้นตอนดังต่อไปนี้ โดยห้ามข้ามขั้นตอน:

---

### ขั้นตอนที่ 1: ตรวจสอบและวิเคราะห์ชุดข้อมูล (Dataset Inspection & Health Check)
1. ตรวจสอบไฟล์ `data/nlu.yml`
2. นับจำนวน Intent ทั้งหมด, จำนวนประโยคตัวอย่าง (Examples) ต่อ Intent และคำนวณสัดส่วนเปอร์เซ็นต์ (%)
3. ตรวจสอบ Entity ทั้งหมดที่ถูกกำกับไว้ (เช่น weight, height, goal, activity_level, age, gender) และนับความถี่
4. ตรวจสอบว่ามี Intent ใดที่มีตัวอย่างน้อยเกินไป (< 5 ตัวอย่าง) หรือมีความไม่สมดุลของข้อมูล (Class Imbalance) หรือไม่

---

### ขั้นตอนที่ 2: การแบ่งชุดข้อมูลสำหรับการฝึกสอนและทดสอบ (Train/Test Split)
1. ทำการแบ่งข้อมูล (Data Splitting) ตามหลักวิชาการแบบ Stratified Train/Test Split (สัดส่วน 80:20)
2. รันคำสั่ง:
   ```bash
   python -m rasa data split nlu -u data/nlu.yml --training-fraction 0.8 --out train_test_split
   ```
3. ตรวจสอบว่าได้ไฟล์ `train_test_split/training_data.yml` และ `train_test_split/test_data.yml` อย่างครบถ้วน

---

### ขั้นตอนที่ 3: ฝึกสอนโมเดล NLU บนชุดฝึกสอน (Train Model on Training Split)
1. ฝึกสอนโมเดลโดยใช้เฉพาะชุด Training Data เพื่อป้องกันปัญหา Data Leakage
2. รันคำสั่ง:
   ```bash
   python -m rasa train nlu --nlu train_test_split/training_data.yml --config config.yml --out models_eval
   ```
3. ระบุชื่อไฟล์โมเดล `.tar.gz` ล่าสุดที่สร้างเสร็จสมบูรณ์

---

### ขั้นตอนที่ 4: ทดสอบประสิทธิภาพโมเดลบนชุดทดสอบ (Evaluate on Test Set)
1. ประเมินโมเดลกับ Test Data (20% ที่โมเดลไม่เคยพบมาก่อน)
2. รันคำสั่ง:
   ```bash
   python -m rasa test nlu --nlu train_test_split/test_data.yml --model models_eval/<ชื่อไฟล์โมเดลล่าสุด>.tar.gz --out evaluation_results
   ```
3. ตรวจสอบไฟล์ผลลัพธ์ใน `evaluation_results/` เช่น `intent_report.json`, `intent_confusion_matrix.png`, `DIETClassifier_report.json`

---

### ขั้นตอนที่ 5: สกัดและวิเคราะห์ค่าสถิติความแม่นยำ (Metrics Extraction)
1. อ่านไฟล์ `evaluation_results/intent_report.json`
2. สกัดค่าสถิติหลักออกมาเป็นตัวเลขที่ชัดเจน:
   - **Overall Accuracy (%)**
   - **Macro Average**: Precision, Recall, F1-Score
   - **Weighted Average**: Precision, Recall, F1-Score
   - **Per-Intent Breakdown**: Precision, Recall, F1-Score, Support ของทุก Intent
3. สกัดผลการสกัด Entity จาก `DIETClassifier_report.json` (ถ้ามี)

---

### ขั้นตอนที่ 6: วิเคราะห์เมทริกซ์ความสับสน (Confusion Matrix & Error Analysis)
1. ตรวจสอบภาพ `evaluation_results/intent_confusion_matrix.png`
2. ทำตาราง Cross-tabulation / Confusion Matrix สรุป Intent ที่จำแนกถูกต้อง และ Intent ที่เกิดความสับสน (Misclassified)
3. อภิปรายสาเหตุของการทายผิด (เช่น การซ้อนทับกันของประโยคสั้น หรือการละเว้นคีย์เวิร์ดสำคัญ)

---

### ขั้นตอนที่ 7: ทดสอบระบบปฏิเสธคำถามนอกขอบเขต (Fallback & Out-of-Scope Test)
1. ทดสอบเกณฑ์ FallbackClassifier (Confidence Threshold = 0.40 ใน `config.yml`)
2. ทดสอบชุดประโยคนอกขอบเขต (Out-of-Scope: OOS) อย่างน้อย 10 ประโยค (เช่น ถามผลหวย, แนะนำเพลง, สอบถามอากาศ, ซ่อมคอมพิวเตอร์)
3. ทดสอบชุดประโยคในขอบเขต (In-Domain) อย่างน้อย 8 ประโยค (เช่น ทักทาย, ถาม BMI, ส่งค่าน้ำหนักส่วนสูง, ขอเมนูอาหาร)
4. คำนวณ **Out-of-Scope Rejection Rate (%)** = (จำนวนประโยค OOS ที่เข้าสู่ Fallback / จำนวนประโยค OOS ทั้งหมด) * 100

---

### ขั้นตอนที่ 8: สร้างรายงาน Artifact สำหรับบทที่ 4 (Generate Chapter 4 Report)
1. สรุปผลการทดลองทั้งหมดและเขียนลงในไฟล์ `CHAPTER_4_EVALUATION_REPORT.md`
2. รูปแบบการจัดหน้าต้องเป็นไปตามมาตรฐานการเขียนรายงานทางวิชาการ (เล่มโครงงาน/วิทยานิพนธ์) โดยมีหัวข้อดังนี้:
   - **4.1 ข้อมูลชุดข้อมูลและการแบ่งส่วนข้อมูล (Dataset Distribution & Splitting)** -> มีตารางแสดงจำนวนตัวอย่างและ % ของแต่ละ Intent
   - **4.2 ผลการทดสอบการจำแนกเจตนา (Intent Classification Performance)** -> มีตาราง Intent Report พร้อม Accuracy, Macro F1, Weighted F1
   - **4.3 ผลการทดสอบการสกัดเอนทิตี (Entity Extraction Performance)** -> มีตารางระบุค่า Precision, Recall, F1 ของแต่ละ Entity
   - **4.4 การวิเคราะห์เมทริกซ์ความสับสน (Confusion Matrix & Error Analysis)** -> ภาพหรือไดอะแกรมประกอบ พร้อมการวิเคราะห์ข้อผิดพลาด
   - **4.5 ผลการทดสอบกรณีคำถามนอกขอบเขตและระบบตอบกลับอัตโนมัติ (Fallback & Out-of-Scope Handling)** -> ตารางผลลัพธ์พร้อมค่าความมั่นใจ (Confidence Score) และ Rejection Rate
   - **4.6 อภิปรายผลการทดลองและสรุปผล (Discussion & Conclusion)** -> สรุปจุดเด่นและข้อเสนอแนะเชิงวิชาการ

> **หมายเหตุสำหรับ AI Agent:** คุณสามารถรันสคริปต์อัตโนมัติ `python evaluate_pipeline.py` เพื่อดำเนินการทุกขั้นตอนข้างต้นให้เสร็จสิ้นได้ในคำสั่งเดียว!
```
