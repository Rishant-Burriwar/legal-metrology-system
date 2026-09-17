import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def create_sample_labels():
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample_images"))
    os.makedirs(sample_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Single-Image Benchmark Labels (Legacy Compatibility)
    # -------------------------------------------------------------------------
    # 1A. Fully Compliant Label
    img1 = Image.new("RGB", (700, 520), color=(255, 255, 255))
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle([(10, 10), (690, 510)], outline=(30, 41, 59), width=3)
    draw1.rectangle([(15, 15), (685, 75)], fill=(37, 99, 235))
    draw1.text((30, 30), "NUTRICRUNCH ALMOND COOKIES", fill=(255, 255, 255))

    lines1 = [
        "Manufactured by: Suncrest Foods Pvt. Ltd., Plot 42, Okhla Ind Area, New Delhi - 110020",
        "Net Quantity: 250 g",
        "MRP: Rs. 85.00 (incl. of all taxes)",
        "Mfg Date: 08/2026",
        "Customer Care: 1800-112-4999, care@suncrestfoods.in",
        "FSSAI Lic No: 10015011000234",
        "Country of Origin: India",
    ]
    y = 100
    for line in lines1:
        draw1.text((35, y), line, fill=(15, 23, 42))
        y += 50
    draw1.rectangle([(30, 460), (670, 495)], outline=(100, 116, 139), width=1)
    draw1.text((40, 470), "Store in cool, dry hygienic place. Consume within 6 months.", fill=(71, 85, 105))
    img1.save(os.path.join(sample_dir, "compliant_label.png"))

    # 1B. Non-Compliant Label
    img2 = Image.new("RGB", (700, 450), color=(255, 250, 240))
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([(10, 10), (690, 440)], outline=(185, 28, 28), width=3)
    draw2.rectangle([(15, 15), (685, 75)], fill=(185, 28, 28))
    draw2.text((30, 30), "CHOCODELIGHT PREMIUM BAR", fill=(255, 255, 255))

    lines2 = [
        "Manufactured by: ChocoWorks Ltd",
        "Net Quantity: 50 g",
        "MRP: Rs. 40.00",  # Missing 'incl. of all taxes'
        "Mfg Date: 12/2025",
        "Ingredients: Cocoa, Sugar, Milk solids",
    ]
    y = 100
    for line in lines2:
        draw2.text((35, y), line, fill=(15, 23, 42))
        y += 50
    img2.save(os.path.join(sample_dir, "non_compliant_label.png"))

    # 1C. Partial Compliant Label
    img3 = Image.new("RGB", (700, 480), color=(248, 250, 252))
    draw3 = ImageDraw.Draw(img3)
    draw3.rectangle([(10, 10), (690, 470)], outline=(5, 150, 105), width=3)
    draw3.rectangle([(15, 15), (685, 75)], fill=(5, 150, 105))
    draw3.text((30, 30), "HIMALAYAN HERBAL HANDMADE SOAP", fill=(255, 255, 255))

    lines3 = [
        "Manufactured by: AyurVeda Organics Ltd, Dehradun, Uttarakhand - 248001",
        "Net Quantity: 125 g",
        "MRP: Rs. 65.00 (incl. of all taxes)",
        "PKD: 05/2026",
        "Consumer Helpline: 9876543210",  # Phone only, email missing
        "Country of Origin: India",
    ]
    y = 100
    for line in lines3:
        draw3.text((35, y), line, fill=(15, 23, 42))
        y += 50
    img3.save(os.path.join(sample_dir, "partial_label.png"))

    # 1D. Blurry Label
    from PIL import ImageFilter
    img_blur = img1.copy().filter(ImageFilter.GaussianBlur(radius=5))
    img_blur.save(os.path.join(sample_dir, "blurry_label.png"))

    # 1E. Low-Resolution Label
    img_lowres = img1.copy().resize((180, 130))
    img_lowres.save(os.path.join(sample_dir, "low_res_label.png"))

    # -------------------------------------------------------------------------
    # 2. Multi-Angle Package Set A: NutriCrunch Almond Cookies (Compliant + PI)
    # -------------------------------------------------------------------------
    # 2A: Front Face (Principal Display Panel)
    front_img = Image.new("RGB", (640, 520), color=(255, 255, 255))
    df = ImageDraw.Draw(front_img)
    df.rectangle([(10, 10), (630, 510)], outline=(20, 83, 45), width=3)
    df.rectangle([(15, 15), (625, 80)], fill=(22, 101, 52))
    df.text((30, 32), "SUNCREST FOODS - PREMIUM RANGE", fill=(255, 255, 255))
    df.text((30, 110), "NUTRICRUNCH ALMOND COOKIES", fill=(22, 101, 52))
    df.text((30, 160), "Crispy, Oven-Baked with California Almonds", fill=(71, 85, 105))
    df.rectangle([(30, 210), (610, 290)], fill=(240, 253, 244), outline=(187, 247, 208))
    df.text((45, 230), "Net Quantity: 250 g", fill=(15, 23, 42))
    df.text((45, 255), "MRP: Rs. 85.00 (incl. of all taxes)", fill=(15, 23, 42))
    df.rectangle([(30, 320), (610, 480)], outline=(226, 232, 240))
    df.text((45, 340), "Serving Suggestion: Best enjoyed with tea or warm milk.", fill=(100, 116, 139))
    df.text((45, 380), "[VEG LOGO] 100% Vegetarian Certified", fill=(22, 101, 52))
    df.text((45, 420), "Front Principal Display Panel - Face A", fill=(148, 163, 184))
    front_img.save(os.path.join(sample_dir, "nutricrunch_front.png"))

    # 2B: Back Face (Statutory Declarations Panel)
    back_img = Image.new("RGB", (640, 520), color=(255, 255, 255))
    db = ImageDraw.Draw(back_img)
    db.rectangle([(10, 10), (630, 510)], outline=(30, 41, 59), width=3)
    db.rectangle([(15, 15), (625, 65)], fill=(30, 41, 59))
    db.text((30, 28), "MANDATORY STATUTORY DECLARATIONS - RULE 6", fill=(255, 255, 255))
    back_lines = [
        "Manufactured by: Suncrest Foods Pvt. Ltd.",
        "Plot 42, Okhla Industrial Area Phase-III, New Delhi - 110020",
        "Consumer Care: 1800-112-4999 | Email: care@suncrestfoods.in",
        "Address for complaints: Same as manufacturer address",
        "Date of Manufacture: 08/2026   |   Batch No: SC-26084",
        "FSSAI License No: 10015011000234",
        "Country of Origin: India",
        "Unit Sale Price: Rs. 0.34 per g",
    ]
    by = 85
    for bl in back_lines:
        db.text((30, by), bl, fill=(15, 23, 42))
        by += 38
    db.rectangle([(25, 410), (615, 490)], outline=(148, 163, 184))
    db.text((35, 425), "Recycle packaging responsibly. Do not litter.", fill=(100, 116, 139))
    db.text((35, 455), "Back Declaration Panel - Face B", fill=(148, 163, 184))
    back_img.save(os.path.join(sample_dir, "nutricrunch_back.png"))

    # 2C: Side Face (Product Intelligence: Ingredients & Additives)
    side_img = Image.new("RGB", (640, 520), color=(255, 255, 255))
    ds = ImageDraw.Draw(side_img)
    ds.rectangle([(10, 10), (630, 510)], outline=(67, 56, 202), width=3)
    ds.rectangle([(15, 15), (625, 65)], fill=(67, 56, 202))
    ds.text((30, 28), "INGREDIENTS, ADDITIVES & NUTRITIONAL FACTS", fill=(255, 255, 255))
    side_lines = [
        "INGREDIENTS: Refined Wheat Flour (Maida), Sugar, Edible Vegetable",
        "Oil (Palm Oil), California Almonds (8%), Invert Sugar Syrup,",
        "Emulsifier (INS 322 - Soy Lecithin), Raising Agent (INS 500(ii)),",
        "Acidity Regulator (INS 330 - Citric Acid), Preservative (INS 211).",
        "",
        "ALLERGEN ADVICE: Contains Wheat (Gluten), Tree Nuts (Almonds), Soy.",
        "May contain traces of Milk solids and Peanuts.",
        "",
        "NUTRITIONAL INFORMATION (Approx per 100g):",
        "Energy: 480 kcal | Protein: 7.2 g | Carbohydrate: 65.0 g",
        "Added Sugars: 22.0 g | Total Fat: 20.0 g | Saturated Fat: 8.5 g",
        "Sodium: 240 mg | Dietary Fiber: 3.5 g",
    ]
    sy = 85
    for sl in side_lines:
        ds.text((30, sy), sl, fill=(15, 23, 42))
        sy += 30
    side_img.save(os.path.join(sample_dir, "nutricrunch_side.png"))

    # -------------------------------------------------------------------------
    # 3. Multi-Angle Package Set B: ChocoDelight Bar (Non-Compliant + Additives)
    # -------------------------------------------------------------------------
    # 3A: Front Face
    c_front = Image.new("RGB", (640, 480), color=(255, 245, 245))
    dcf = ImageDraw.Draw(c_front)
    dcf.rectangle([(10, 10), (630, 470)], outline=(153, 27, 27), width=3)
    dcf.rectangle([(15, 15), (625, 75)], fill=(153, 27, 27))
    dcf.text((30, 32), "CHOCODELIGHT RICH COCOA BAR", fill=(255, 255, 255))
    dcf.text((30, 110), "ChocoDelight Dark Truffle", fill=(153, 27, 27))
    dcf.text((30, 180), "Net Quantity: 50 g", fill=(15, 23, 42))
    dcf.text((30, 230), "MRP: Rs. 40.00", fill=(15, 23, 42))  # Missing 'incl. of all taxes'
    dcf.text((30, 320), "Front Principal Panel - Face A", fill=(148, 163, 184))
    c_front.save(os.path.join(sample_dir, "chocobar_front.png"))

    # 3B: Back Face
    c_back = Image.new("RGB", (640, 480), color=(255, 245, 245))
    dcb = ImageDraw.Draw(c_back)
    dcb.rectangle([(10, 10), (630, 470)], outline=(153, 27, 27), width=3)
    dcb.rectangle([(15, 15), (625, 75)], fill=(153, 27, 27))
    dcb.text((30, 32), "PRODUCT DETAILS & COMPOSITION", fill=(255, 255, 255))
    dcb_lines = [
        "Manufactured by: ChocoWorks Ltd",  # Missing full address
        "Mfg Date: 12/2025",
        "INGREDIENTS: Sugar, Hydrogenated Vegetable Fat, Cocoa Solids (12%),",
        "Milk Solids, Emulsifier (INS 322), Preservative (INS 211),",
        "Synthetic Food Colours (INS 102 - Tartrazine, INS 110 - Sunset Yellow),",
        "Artificial Sweetener (INS 955 - Sucralose).",
        "ALLERGENS: Contains Milk. May contain Peanuts and Tree nuts.",
        # Note missing Customer Care, missing FSSAI, missing Country of Origin
    ]
    cby = 100
    for cbl in dcb_lines:
        dcb.text((30, cby), cbl, fill=(15, 23, 42))
        cby += 35
    c_back.save(os.path.join(sample_dir, "chocobar_back.png"))

    # -------------------------------------------------------------------------
    # 4. Panorama Sequence: Overlapping Panels of Cylindrical Package
    # -------------------------------------------------------------------------
    # Panel 1: Left & Front Face (Width: 600, overlap ~300)
    pan1 = Image.new("RGB", (600, 450), color=(240, 249, 255))
    dp1 = ImageDraw.Draw(pan1)
    dp1.rectangle([(5, 5), (595, 445)], outline=(2, 132, 199), width=2)
    dp1.text((30, 40), "CYLINDER BOTTLE - 360 DEGREE SCAN (SECTOR 1)", fill=(3, 105, 161))
    dp1.text((30, 100), "AERO DRINK ELECTROLYTE CITRUS", fill=(14, 116, 144))
    dp1.text((30, 160), "Net Quantity: 500 ml", fill=(15, 23, 42))
    dp1.text((30, 210), "MRP: Rs. 50.00 (incl. of all taxes)", fill=(15, 23, 42))
    dp1.text((30, 270), "Shared Surface Marker X1 - Feature Anchor", fill=(100, 116, 139))
    pan1.save(os.path.join(sample_dir, "cylinder_p1.png"))

    # Panel 2: Front & Right Face (overlaps marker and brand)
    pan2 = Image.new("RGB", (600, 450), color=(240, 249, 255))
    dp2 = ImageDraw.Draw(pan2)
    dp2.rectangle([(5, 5), (595, 445)], outline=(2, 132, 199), width=2)
    dp2.text((30, 40), "CYLINDER BOTTLE - 360 DEGREE SCAN (SECTOR 2)", fill=(3, 105, 161))
    dp2.text((30, 100), "MRP: Rs. 50.00 (incl. of all taxes)", fill=(15, 23, 42))
    dp2.text((30, 150), "Shared Surface Marker X1 - Feature Anchor", fill=(100, 116, 139))
    dp2.text((30, 210), "Mfg Date: 07/2026   |   Batch: AD-702", fill=(15, 23, 42))
    dp2.text((30, 260), "FSSAI Lic No: 10019022000876", fill=(15, 23, 42))
    pan2.save(os.path.join(sample_dir, "cylinder_p2.png"))

    # Panel 3: Right & Rear Face
    pan3 = Image.new("RGB", (600, 450), color=(240, 249, 255))
    dp3 = ImageDraw.Draw(pan3)
    dp3.rectangle([(5, 5), (595, 445)], outline=(2, 132, 199), width=2)
    dp3.text((30, 40), "CYLINDER BOTTLE - 360 DEGREE SCAN (SECTOR 3)", fill=(3, 105, 161))
    dp3.text((30, 100), "Manufactured by: Aero Beverage Corp.", fill=(15, 23, 42))
    dp3.text((30, 150), "Plot 18, MIDC Pune, Maharashtra - 411018", fill=(15, 23, 42))
    dp3.text((30, 200), "Consumer Care: 1800-200-9999, care@aerobev.com", fill=(15, 23, 42))
    dp3.text((30, 250), "Country of Origin: India", fill=(15, 23, 42))
    pan3.save(os.path.join(sample_dir, "cylinder_p3.png"))

    # -------------------------------------------------------------------------
    # 5. Synthetic Inspection Video (Rotating Package Sample)
    # -------------------------------------------------------------------------
    video_path = os.path.join(sample_dir, "sample_inspection_video.mp4")
    generate_synthetic_video(video_path, [front_img, side_img, back_img])

    print("All statutory reference benchmark samples successfully created in:", sample_dir)


def generate_synthetic_video(output_path, pil_images, fps=10, duration_sec=4):
    """Generate a clean synthetic MP4 video simulating package rotation."""
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not writer.isOpened():
        print("Warning: Could not open VideoWriter for", output_path)
        return

    # Resize all PIL images to video frame size
    cv_frames = []
    for pimg in pil_images:
        resized = pimg.resize((width, height))
        # Convert PIL RGB to OpenCV BGR
        cv_img = cv2.cvtColor(np.array(resized), cv2.COLOR_RGB2BGR)
        cv_frames.append(cv_img)

    total_frames = fps * duration_sec
    frames_per_view = total_frames // len(cv_frames)

    for i, base_frame in enumerate(cv_frames):
        for f in range(frames_per_view):
            # Add subtle pan/tilt effect to mimic handheld inspection camera
            dx = int(np.sin(f / 3.0) * 4)
            dy = int(np.cos(f / 3.0) * 3)
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            shifted = cv2.warpAffine(base_frame, M, (width, height))
            writer.write(shifted)

    writer.release()
    print("Created synthetic inspection video:", output_path)


if __name__ == "__main__":
    create_sample_labels()
