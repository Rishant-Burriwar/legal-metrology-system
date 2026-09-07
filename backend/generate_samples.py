import os
from PIL import Image, ImageDraw, ImageFont


def create_sample_labels():
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample_images"))
    os.makedirs(sample_dir, exist_ok=True)

    # 1. Fully Compliant Label
    img1 = Image.new("RGB", (700, 520), color=(255, 255, 255))
    draw1 = ImageDraw.Draw(img1)
    # Border & Header
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

    img1_path = os.path.join(sample_dir, "compliant_label.png")
    img1.save(img1_path)
    print(f"Created: {img1_path}")

    # 2. Non-Compliant Label (Missing taxes clause, missing customer care, missing FSSAI)
    img2 = Image.new("RGB", (700, 450), color=(255, 250, 240))
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([(10, 10), (690, 440)], outline=(185, 28, 28), width=3)
    draw2.rectangle([(15, 15), (685, 75)], fill=(185, 28, 28))
    draw2.text((30, 30), "CHOCODELIGHT PREMIUM BAR", fill=(255, 255, 255))

    lines2 = [
        "Manufactured by: ChocoWorks Ltd",
        "Net Quantity: 50 g",
        "MRP: Rs. 40.00",  # Notice missing 'incl. of all taxes'
        "Mfg Date: 12/2025",
        "Ingredients: Cocoa, Sugar, Milk solids",
        # Notice missing customer care, FSSAI, Country of Origin
    ]
    y = 100
    for line in lines2:
        draw2.text((35, y), line, fill=(15, 23, 42))
        y += 50

    img2_path = os.path.join(sample_dir, "non_compliant_label.png")
    img2.save(img2_path)
    print(f"Created: {img2_path}")

    # 3. Partial Compliant / Minor Violation Label
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

    img3_path = os.path.join(sample_dir, "partial_label.png")
    img3.save(img3_path)
    print(f"Created: {img3_path}")

    # 4. Blurry Label (Tests Pre-OCR Quality Gate Rejection)
    from PIL import ImageFilter
    img_blur = img1.copy().filter(ImageFilter.GaussianBlur(radius=5))
    img_blur_path = os.path.join(sample_dir, "blurry_label.png")
    img_blur.save(img_blur_path)
    print(f"Created: {img_blur_path}")

    # 5. Low-Resolution Label (Below 300x200 min dimensions)
    img_lowres = img1.copy().resize((180, 130))
    img_lowres_path = os.path.join(sample_dir, "low_res_label.png")
    img_lowres.save(img_lowres_path)
    print(f"Created: {img_lowres_path}")


if __name__ == "__main__":
    create_sample_labels()

