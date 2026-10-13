"""
setup_db.py – Generates database.sql and initializes MySQL / SQLite database
with complete demo seed data for Foody Hunters.
"""
import os
import sys
import sqlite3
from werkzeug.security import generate_password_hash

# Password hash for 'password123'
DEFAULT_PW_HASH = generate_password_hash("password123")

# 10 Food Categories
CATEGORIES = [
    (1, "Pizza", "🍕", "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400&q=80", 1),
    (2, "Burger", "🍔", "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&q=80", 2),
    (3, "Biryani", "🍛", "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400&q=80", 3),
    (4, "Gujarati", "🥘", "https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?w=400&q=80", 4),
    (5, "South Indian", "🥞", "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=400&q=80", 5),
    (6, "Chinese", "🍜", "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=400&q=80", 6),
    (7, "Punjabi", "🫓", "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&q=80", 7),
    (8, "Desserts", "🍰", "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=400&q=80", 8),
    (9, "Beverages", "🧋", "https://images.unsplash.com/photo-1544145945-f90425340c7e?w=400&q=80", 9),
    (10, "Fast Food", "🍟", "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=400&q=80", 10),
]

# Users (id, name, email, phone, role, address)
USERS = [
    (1, "Raj Patel", "customer@foodyhunters.com", "9876543210", "customer", "B-402, Shivalik Residency, SG Highway, Ahmedabad"),
    (2, "Chef Sanjeev Kumar", "restaurant@foodyhunters.com", "9823456789", "restaurant", "101, Food Street, Vastrapur, Ahmedabad"),
    (3, "Vikram Singh", "delivery@foodyhunters.com", "9812345678", "delivery", "12, Shanti Nagar, Navrangpura, Ahmedabad"),
    (4, "System Administrator", "admin@foodyhunters.com", "9898989898", "admin", "Foody Hunters HQ, Sindhu Bhavan Road, Ahmedabad"),
    (5, "Kavita Shah", "owner.gujarati@foodyhunters.com", "9876500001", "restaurant", "Ashram Road, Ahmedabad"),
    (6, "Mohsin Khan", "owner.biryani@foodyhunters.com", "9876500002", "restaurant", "Relief Road, Ahmedabad"),
    (7, "Amit Sharma", "owner.burger@foodyhunters.com", "9876500003", "restaurant", "Law Garden, Ahmedabad"),
    (8, "Ramaswamy Iyer", "owner.south@foodyhunters.com", "9876500004", "restaurant", "Maninagar, Ahmedabad"),
    (9, "Chen Wei", "owner.chinese@foodyhunters.com", "9876500005", "restaurant", "Bodakdev, Ahmedabad"),
    (10, "Harpreet Singh", "owner.punjabi@foodyhunters.com", "9876500006", "restaurant", "Prahlad Nagar, Ahmedabad"),
    (11, "Pooja Mehta", "owner.dessert@foodyhunters.com", "9876500007", "restaurant", "Paldi, Ahmedabad"),
    (12, "Neha Verma", "owner.healthy@foodyhunters.com", "9876500008", "restaurant", "Thaltej, Ahmedabad"),
    (13, "Arun Kumar", "partner2@foodyhunters.com", "9811122233", "delivery", "Ghatlodia, Ahmedabad"),
]

# 10 Restaurants (id, owner_id, name, description, cuisine, address, phone, rating, delivery_time, delivery_fee, min_order, image, status)
RESTAURANTS = [
    (1, 2, "Pizza Palace", "Artisan wood-fired Italian pizzas, pastas, and cheesy garlic breads baked to perfection.", "Pizza, Italian, Fast Food", "Shop 14, Alpha One Mall, Vastrapur, Ahmedabad", "079-26851122", 4.8, "25-35 min", 35.00, 150.00, "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&q=80", "approved"),
    (2, 5, "Royal Gujarati Thali", "Authentic Kathiyawadi & Gujarati thali with unlimited puran poli, dhokla and farsan.", "Gujarati, Traditional, Thali", "Opp. Town Hall, Ashram Road, Ahmedabad", "079-26584433", 4.9, "30-40 min", 40.00, 200.00, "https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?w=600&q=80", "approved"),
    (3, 6, "Urban Biryani", "Hyderabadi Dum Biryani cooked in sealed clay pots with royal aromatic saffron.", "Biryani, Mughlai, Hyderabadi", "Near Kalupur Gate, Relief Road, Ahmedabad", "079-22137788", 4.7, "35-45 min", 45.00, 250.00, "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&q=80", "approved"),
    (4, 7, "Burger Hub", "Gourmet smashed burgers, loaded cheese fries, and thick American milkshakes.", "Burgers, American, Fast Food", "Near Law Garden Night Market, Ellisbridge, Ahmedabad", "079-26405566", 4.6, "20-30 min", 30.00, 120.00, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&q=80", "approved"),
    (5, 8, "South Indian Kitchen", "Crispy ghee roast dosas, steamed fluffy idlis, vada, and authentic filter coffee.", "South Indian, Dosa, Idli", "Station Road, Maninagar, Ahmedabad", "079-25461100", 4.8, "20-30 min", 30.00, 100.00, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&q=80", "approved"),
    (6, 9, "Chinese Wok & Dim Sum", "Sizzling Hakka noodles, Manchurian gravy, dim sums, and fiery Schezwan rice.", "Chinese, Asian, Noodles", "Sindhu Bhavan Road, Bodakdev, Ahmedabad", "079-29703344", 4.5, "30-40 min", 40.00, 180.00, "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600&q=80", "approved"),
    (7, 10, "Punjabi Rasoi", "Rich Butter Chicken, Dal Makhani slow-cooked overnight, garlic naans and tandoori grills.", "Punjabi, North Indian, Tandoor", "Dev Aurum, Prahlad Nagar, Ahmedabad", "079-26938877", 4.7, "30-40 min", 40.00, 200.00, "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80", "approved"),
    (8, 11, "Dessert House & Bakery", "Handcrafted cheesecakes, Belgian waffles, chocolate lava cakes and macarons.", "Desserts, Bakery, Waffles", "Mahalaxmi Crossroads, Paldi, Ahmedabad", "079-26629911", 4.9, "15-25 min", 25.00, 150.00, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&q=80", "approved"),
    (9, 12, "Healthy Bowl Co.", "Nutritious macro bowls, fresh cold-pressed detox juices, and protein salads.", "Healthy, Salads, Smoothies", "Opp. Rajpath Club, SG Highway, Ahmedabad", "079-29707766", 4.6, "25-35 min", 35.00, 180.00, "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&q=80", "approved"),
    (10, 2, "Spice Garden Bistro", "Royal Mughal spices and contemporary fusion street delicacies in a lavish menu.", "North Indian, Street Food, Mughlai", "Near Iscon Cross Road, Satellite, Ahmedabad", "079-26925500", 4.7, "30-40 min", 40.00, 200.00, "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&q=80", "approved"),
]

# 60+ Food Items (id, restaurant_id, category_id, name, description, price, image, veg_type, availability, rating)
FOOD_ITEMS = [
    # Restaurant 1: Pizza Palace
    (1, 1, 1, "Margherita Classic Pizza", "Classic San Marzano tomato sauce, fresh mozzarella fior di latte, and basil leaves.", 249.00, "https://images.unsplash.com/photo-1604382355076-af4b0eb60143?w=500&q=80", "veg", 1, 4.8),
    (2, 1, 1, "Farmhouse Veggie Overload", "Crisp bell peppers, red onions, juicy mushrooms, black olives, and sweet golden corn.", 299.00, "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500&q=80", "veg", 1, 4.7),
    (3, 1, 1, "Peri Peri Paneer Feast", "Spicy marinated cottage cheese chunks, jalapeños, red paprika, and peri peri drizzle.", 349.00, "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=500&q=80", "veg", 1, 4.9),
    (4, 1, 1, "Smoked BBQ Chicken Pizza", "Tender smoked chicken cubes tossed in hickory BBQ sauce with molten cheddar.", 379.00, "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=500&q=80", "non_veg", 1, 4.8),
    (5, 1, 10, "Cheesy Garlic Breadsticks", "Freshly baked herb breadsticks stuffed with molten mozzarella, served with marinara dip.", 149.00, "https://images.unsplash.com/photo-1619895092538-128341789043?w=500&q=80", "veg", 1, 4.6),
    (6, 1, 9, "Italian Peach Iced Tea", "Refreshing cold brewed black tea infused with real Italian peach pulp and mint.", 99.00, "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=500&q=80", "veg", 1, 4.5),

    # Restaurant 2: Royal Gujarati Thali
    (7, 2, 4, "Royal Kathiyawadi Thali", "Ringna No Olo, Sev Tameta, Bajra No Rotlo, Puran Poli, Dal Baati, Buttermilk & Jalebi.", 279.00, "https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?w=500&q=80", "veg", 1, 5.0),
    (8, 2, 4, "Gujarati Special Thali", "4 Sabzi, Phulka Roti, Khatti Meethi Gujarati Dal, Steamed Rice, Farsan, Chaas & Sweet.", 239.00, "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=500&q=80", "veg", 1, 4.9),
    (9, 2, 4, "Khaman Dhokla Platter", "Spongy steamed gram flour cakes tempered with mustard seeds, curry leaves & green chilies.", 99.00, "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&q=80", "veg", 1, 4.7),
    (10, 2, 4, "Surti Sev Khamani", "Crushed chana dal delicacy cooked in ghee with ginger-chili paste and fresh coriander.", 119.00, "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=500&q=80", "veg", 1, 4.8),
    (11, 2, 9, "Masala Chaas Matka", "Traditional probiotic spiced buttermilk blended with roasted cumin, mint, and black salt.", 49.00, "https://images.unsplash.com/photo-1544145945-f90425340c7e?w=500&q=80", "veg", 1, 4.9),
    (12, 2, 8, "Kesar Pista Shrikhand", "Velvety strained yogurt dessert infused with Kashmiri saffron strands and pistachios.", 129.00, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=500&q=80", "veg", 1, 4.8),

    # Restaurant 3: Urban Biryani
    (13, 3, 3, "Dum Hyderabadi Chicken Biryani", "Layered long-grain Basmati rice and chicken marinated in yogurt and royal spices.", 299.00, "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=500&q=80", "non_veg", 1, 4.9),
    (14, 3, 3, "Royal Mutton Dum Biryani", "Succulent tender goat meat cuts slow-cooked with basmati rice in dum sealed handi.", 389.00, "https://images.unsplash.com/photo-1633945274405-b6c8069047b0?w=500&q=80", "non_veg", 1, 4.8),
    (15, 3, 3, "Shahi Veg Dum Biryani", "Assorted seasonal garden vegetables, paneer cubes, and golden fried onions with mint.", 249.00, "https://images.unsplash.com/photo-1642821373181-696a54913e9a?w=500&q=80", "veg", 1, 4.6),
    (16, 3, 3, "Paneer Makhani Biryani", "Soft cottage cheese tikka tossed in rich makhani gravy layered with saffron rice.", 269.00, "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=500&q=80", "veg", 1, 4.7),
    (17, 3, 7, "Chicken Seekh Kebab (4 pcs)", "Minced chicken seasoned with fresh herbs and skewered in clay tandoor oven.", 229.00, "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?w=500&q=80", "non_veg", 1, 4.7),
    (18, 3, 9, "Royal Rose Badam Sharbat", "Chilled milk shake infused with fragrant Gulab rose syrup and crushed almonds.", 89.00, "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=500&q=80", "veg", 1, 4.6),

    # Restaurant 4: Burger Hub
    (19, 4, 2, "Ultimate Crispy Paneer Burger", "Crispy spiced paneer patty topped with coleslaw, chipotle mayo, and cheddar slice.", 179.00, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500&q=80", "veg", 1, 4.7),
    (20, 4, 2, "Smoky Crunch Chicken Burger", "Fried chicken fillet with smoky barbecue glaze, pickles, and melted cheese in brioche bun.", 219.00, "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=500&q=80", "non_veg", 1, 4.8),
    (21, 4, 2, "Aloo Tikki Street Crunch Burger", "Spiced golden potato patty, tangy mint mayonnaise, crunchy onions and tomatoes.", 99.00, "https://images.unsplash.com/photo-1550547660-d9450f859349?w=500&q=80", "veg", 1, 4.5),
    (22, 4, 10, "Cheesy Peri Peri Loaded Fries", "Crispy french fries generously dusted with peri peri spice and drizzled with molten cheese.", 149.00, "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=500&q=80", "veg", 1, 4.9),
    (23, 4, 9, "Belgian Chocolate Shake", "Thick creamy shake blended with dark Belgian chocolate and topped with choco chips.", 139.00, "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=500&q=80", "veg", 1, 4.8),

    # Restaurant 5: South Indian Kitchen
    (24, 5, 5, "Mysore Masala Dosa", "Crispy golden fermented crepe lined with fiery red garlic chutney & spiced potato filling.", 149.00, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=500&q=80", "veg", 1, 4.9),
    (25, 5, 5, "Cheese Burst Paper Roast Dosa", "Paper-thin extra large dosa coated with generous molten mozzarella and amul butter.", 189.00, "https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?w=500&q=80", "veg", 1, 4.8),
    (26, 5, 5, "Steamed Ghee Podi Idli (4 pcs)", "Mini soft idlis tossed in fragrant gun powder spice (Podi) and pure desi cow ghee.", 119.00, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=500&q=80", "veg", 1, 4.7),
    (27, 5, 5, "Medu Vada with Sambar (2 pcs)", "Crispy golden lentil fritters served with piping hot vegetable drumstick sambar.", 89.00, "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=500&q=80", "veg", 1, 4.6),
    (28, 5, 9, "Degree Filter Coffee", "Authentic South Indian chicory-roasted drip coffee frothed with boiling whole milk.", 59.00, "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=500&q=80", "veg", 1, 5.0),

    # Restaurant 6: Chinese Wok & Dim Sum
    (29, 6, 6, "Veg Hakka Noodles", "Wok-tossed julienne vegetables and wheat noodles in aromatic sesame oil and soy sauce.", 169.00, "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=500&q=80", "veg", 1, 4.7),
    (30, 6, 6, "Veg Manchurian Gravy", "Crisp vegetable dumplings simmered in a dark, glossy, pungent ginger-garlic sauce.", 189.00, "https://images.unsplash.com/photo-1525755662778-989d0524087e?w=500&q=80", "veg", 1, 4.6),
    (31, 6, 6, "Schezwan Chicken Fried Rice", "Wok-fried jasmine rice tossed with chicken cubes and spicy house-made Schezwan paste.", 229.00, "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=500&q=80", "non_veg", 1, 4.8),
    (32, 6, 6, "Steamed Dim Sum Momos (6 pcs)", "Translucent steamed dumplings filled with finely minced spiced vegetables & dipping sauce.", 139.00, "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=500&q=80", "veg", 1, 4.7),
    (33, 6, 6, "Crispy Honey Chilli Potatoes", "Double-fried crispy potato batons glazed in honey, toasted sesame seeds, and red chili.", 149.00, "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=500&q=80", "veg", 1, 4.5),

    # Restaurant 7: Punjabi Rasoi
    (34, 7, 7, "Paneer Butter Masala", "Cubes of fresh malai paneer simmered in a rich tomato, butter, and cashew cream gravy.", 249.00, "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&q=80", "veg", 1, 4.9),
    (35, 7, 7, "Dal Makhani (Slow-Cooked)", "Black lentils and kidney beans slow-simmered for 16 hours with butter and cream.", 199.00, "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=500&q=80", "veg", 1, 4.9),
    (36, 7, 7, "Amritsari Kulcha with Chole", "Crispy layered stuffed flatbread served with tangy spicy Amritsari chickpea curry.", 179.00, "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=500&q=80", "veg", 1, 4.8),
    (37, 7, 7, "Butter Chicken (Murgh Makhani)", "Charcoal grilled tandoori chicken cooked in velvety tomato, makhani butter sauce.", 299.00, "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?w=500&q=80", "non_veg", 1, 4.9),
    (38, 7, 7, "Butter Garlic Naan", "Leavened oven-baked flatbread brushed with garlic butter and fresh coriander.", 49.00, "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&q=80", "veg", 1, 4.8),
    (39, 7, 9, "Patiala Sweet Lassi", "Thick creamy Punjabi yogurt beverage crowned with fresh clotted malai and pistachios.", 79.00, "https://images.unsplash.com/photo-1544145945-f90425340c7e?w=500&q=80", "veg", 1, 4.7),

    # Restaurant 8: Dessert House & Bakery
    (40, 8, 8, "Belgian Waffle with Nutella", "Golden crisp Belgian waffle smothered in hot Nutella, fresh strawberries and cream.", 189.00, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=500&q=80", "veg", 1, 4.9),
    (41, 8, 8, "Sizzling Chocolate Brownie", "Fudgy walnut brownie served on a hot iron skillet with vanilla gelato & chocolate fudge.", 169.00, "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=500&q=80", "veg", 1, 5.0),
    (42, 8, 8, "New York Baked Cheesecake", "Classic dense and creamy New York style cheesecake on a crunchy graham cracker crust.", 219.00, "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?w=500&q=80", "veg", 1, 4.8),
    (43, 8, 8, "Gulab Jamun with Ice Cream", "Warm soft cottage cheese dumplings soaked in rose sugar syrup paired with vanilla bean scoop.", 119.00, "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&q=80", "veg", 1, 4.7),
    (44, 8, 9, "Oreo Overload Cold Coffee", "Frosty brewed espresso blended with vanilla ice cream and chunky crushed Oreo cookies.", 129.00, "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=500&q=80", "veg", 1, 4.8),

    # Restaurant 9: Healthy Bowl Co.
    (45, 9, 10, "Mediterranean Quinoa Bowl", "Fluffy quinoa, grilled halloumi, cherry tomatoes, kalamata olives, cucumber, & tahini.", 239.00, "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500&q=80", "veg", 1, 4.7),
    (46, 9, 10, "Grilled Chicken Avocado Salad", "Sous-vide chicken breast, hass avocado, mixed greens, walnuts, and lemon vinaigrette.", 279.00, "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=500&q=80", "non_veg", 1, 4.8),
    (47, 9, 9, "Berry Blast Detox Smoothie", "Antioxidant-packed blueberries, strawberries, chia seeds, and unsweetened Greek yogurt.", 149.00, "https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=500&q=80", "veg", 1, 4.6),
    (48, 9, 9, "Cold-Pressed Green Glow Juice", "Refreshing elixir of green apple, celery, spinach, cucumber, ginger, and Meyer lemon.", 129.00, "https://images.unsplash.com/photo-1613478223719-2ab802602423?w=500&q=80", "veg", 1, 4.5),

    # Restaurant 10: Spice Garden Bistro
    (49, 10, 7, "Tandoori Paneer Tikka", "Charred cottage cheese cubes marinated in spiced yogurt, fenugreek, and mustard oil.", 229.00, "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?w=500&q=80", "veg", 1, 4.8),
    (50, 10, 7, "Mutton Rogan Josh", "Kashmiri delicacy of tender mutton cooked in aromatic gravy flavored with alkanet root.", 399.00, "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?w=500&q=80", "non_veg", 1, 4.9),
    (51, 10, 10, "Dahi Puri Chaat Explosion", "Crisp puffed puris filled with potatoes, sweetened curd, tamarind chutney, and sev.", 119.00, "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&q=80", "veg", 1, 4.9),
    (52, 10, 10, "Pav Bhaji (Amul Butter Special)", "Mashed spiced vegetable curry cooked on a tawa with generous dollops of butter.", 159.00, "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=500&q=80", "veg", 1, 4.8),
    (53, 10, 9, "Fresh Mint Mojito", "Muddled fresh mint leaves, lime wedges, cane sugar, and sparkling soda on crushed ice.", 99.00, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=500&q=80", "veg", 1, 4.6),
]

# Coupons (id, code, description, discount_type, discount_value, max_discount, min_order_amount, expiry_date, usage_limit, is_active)
COUPONS = [
    (1, "WELCOME50", "Get 50% discount on your first food order up to ₹100", "percentage", 50.00, 100.00, 199.00, "2027-12-31", 1000, 1),
    (2, "FOOD20", "Flat 20% off on all restaurants on orders above ₹299", "percentage", 20.00, 150.00, 299.00, "2027-12-31", 1000, 1),
    (3, "HUNTER10", "Save 10% on every meal with no minimum order", "percentage", 10.00, 80.00, 99.00, "2027-12-31", 1000, 1),
    (4, "FLAT100", "Special Flat ₹100 savings on orders above ₹499", "fixed", 100.00, 100.00, 499.00, "2027-12-31", 1000, 1),
]

# Addresses (id, user_id, label, address, city, pincode, is_default)
ADDRESSES = [
    (1, 1, "Home", "Flat 402, Shivalik Residency, Near SG Highway", "Ahmedabad", "380054", 1),
    (2, 1, "Work", "Floor 6, Synergy Tower, Prahlad Nagar", "Ahmedabad", "380015", 0),
]

# Delivery Partners (id, user_id, vehicle_type, vehicle_number, license_number, is_available)
DELIVERY_PARTNERS = [
    (1, 3, "Motorcycle", "GJ-01-EE-4521", "DL-GJ01-2022-87654", 1),
    (2, 13, "Scooter", "GJ-01-AB-9876", "DL-GJ01-2021-12345", 1),
]

# Reviews (id, user_id, restaurant_id, order_id, rating, comment)
REVIEWS = [
    (1, 1, 1, 1, 5, "Best pizza in town! The crust was wonderfully crispy and the cheese was super fresh. Loved the fast delivery!"),
    (2, 1, 2, None, 5, "Authentic Gujarati Thali taste. Felt just like homemade food with royal touch! Must try Puran Poli."),
    (3, 1, 3, None, 5, "Urban Biryani's dum chicken biryani is unbeatable in Ahmedabad. So aromatic and flavorful."),
    (4, 1, 4, None, 4, "Cheesy loaded fries were great and burger patty was really crunchy."),
    (5, 1, 5, None, 5, "Mysore Masala Dosa with that red chutney is heavenly. Genuine Bangalore style!"),
    (6, 1, 8, None, 5, "Belgian waffles with hot Nutella were an absolute delight. Delivered warm!"),
]

# Demo Orders (id, order_code, user_id, restaurant_id, address_id, total_amount, delivery_fee, discount, tax, payment_method, payment_status, order_status, coupon_id, notes)
ORDERS = [
    (1, "FH-20241001-A1B2C3", 1, 1, 1, 496.00, 35.00, 50.00, 21.00, "demo_upi", "paid", "delivered", 1, "Please provide extra oregano sachets"),
    (2, "FH-20241002-D4E5F6", 1, 2, 1, 310.00, 40.00, 0.00, 14.00, "cod", "pending", "preparing", None, "Ring doorbell twice"),
]

ORDER_ITEMS = [
    (1, 1, 1, 1, 249.00, 249.00),
    (2, 1, 5, 1, 149.00, 149.00),
    (3, 1, 6, 1, 99.00, 99.00),
    (4, 2, 7, 1, 279.00, 279.00),
]

DELIVERY_ASSIGNMENTS = [
    (1, 1, 3, "delivered"),
    (2, 2, 3, "assigned"),
]

PAYMENTS = [
    (1, 1, "TXN202410019876", "", "demo_upi", 496.00, "paid"),
]


SQL_SCHEMA = """-- ========================================================
-- FOODY HUNTERS - Online Food Delivery System
-- Complete MySQL Database Schema and Seed Data
-- Target Database: foody_hunters (XAMPP MySQL)
-- ========================================================

CREATE DATABASE IF NOT EXISTS `foody_hunters` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `foody_hunters`;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `admin_logs`;
DROP TABLE IF EXISTS `complaints`;
DROP TABLE IF EXISTS `delivery_assignments`;
DROP TABLE IF EXISTS `delivery_partners`;
DROP TABLE IF EXISTS `reviews`;
DROP TABLE IF EXISTS `payments`;
DROP TABLE IF EXISTS `order_items`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `coupons`;
DROP TABLE IF EXISTS `addresses`;
DROP TABLE IF EXISTS `cart_items`;
DROP TABLE IF EXISTS `cart`;
DROP TABLE IF EXISTS `food_items`;
DROP TABLE IF EXISTS `restaurant_categories`;
DROP TABLE IF EXISTS `food_categories`;
DROP TABLE IF EXISTS `restaurants`;
DROP TABLE IF EXISTS `users`;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) NOT NULL UNIQUE,
  `phone` VARCHAR(20) DEFAULT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('customer', 'restaurant', 'delivery', 'admin') DEFAULT 'customer',
  `address` TEXT DEFAULT NULL,
  `status` ENUM('active', 'inactive') DEFAULT 'active',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `restaurants` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `owner_id` INT DEFAULT NULL,
  `name` VARCHAR(150) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `cuisine` VARCHAR(100) NOT NULL,
  `address` TEXT NOT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `rating` DECIMAL(3,1) DEFAULT 4.5,
  `delivery_time` VARCHAR(30) DEFAULT '30-40 min',
  `delivery_fee` DECIMAL(6,2) DEFAULT 40.00,
  `min_order` DECIMAL(6,2) DEFAULT 100.00,
  `image` VARCHAR(255) DEFAULT NULL,
  `status` ENUM('pending', 'approved', 'rejected') DEFAULT 'approved',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`owner_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `food_categories` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL UNIQUE,
  `icon` VARCHAR(50) DEFAULT '🍽️',
  `image` VARCHAR(255) DEFAULT NULL,
  `sort_order` INT DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `restaurant_categories` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `restaurant_id` INT NOT NULL,
  `category_id` INT NOT NULL,
  FOREIGN KEY (`restaurant_id`) REFERENCES `restaurants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`category_id`) REFERENCES `food_categories`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `food_items` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `restaurant_id` INT NOT NULL,
  `category_id` INT NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `price` DECIMAL(8,2) NOT NULL,
  `image` VARCHAR(255) DEFAULT NULL,
  `veg_type` ENUM('veg', 'non_veg') DEFAULT 'veg',
  `availability` TINYINT(1) DEFAULT 1,
  `rating` DECIMAL(3,1) DEFAULT 4.5,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`restaurant_id`) REFERENCES `restaurants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`category_id`) REFERENCES `food_categories`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `cart` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `status` ENUM('active', 'completed', 'abandoned') DEFAULT 'active',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `cart_items` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `cart_id` INT NOT NULL,
  `food_item_id` INT NOT NULL,
  `quantity` INT DEFAULT 1,
  `price` DECIMAL(8,2) NOT NULL,
  FOREIGN KEY (`cart_id`) REFERENCES `cart`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`food_item_id`) REFERENCES `food_items`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `addresses` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `label` VARCHAR(50) DEFAULT 'Home',
  `address` TEXT NOT NULL,
  `city` VARCHAR(50) DEFAULT 'Ahmedabad',
  `pincode` VARCHAR(10) DEFAULT '380001',
  `is_default` TINYINT(1) DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `coupons` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `code` VARCHAR(50) NOT NULL UNIQUE,
  `description` VARCHAR(255) DEFAULT NULL,
  `discount_type` ENUM('percentage', 'fixed') DEFAULT 'percentage',
  `discount_value` DECIMAL(6,2) NOT NULL,
  `max_discount` DECIMAL(6,2) DEFAULT NULL,
  `min_order_amount` DECIMAL(8,2) DEFAULT 0.00,
  `expiry_date` DATE DEFAULT NULL,
  `usage_limit` INT DEFAULT 1000,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `orders` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `order_code` VARCHAR(50) NOT NULL UNIQUE,
  `user_id` INT NOT NULL,
  `restaurant_id` INT NOT NULL,
  `address_id` INT DEFAULT NULL,
  `total_amount` DECIMAL(10,2) NOT NULL,
  `delivery_fee` DECIMAL(6,2) DEFAULT 40.00,
  `discount` DECIMAL(6,2) DEFAULT 0.00,
  `tax` DECIMAL(6,2) DEFAULT 0.00,
  `payment_method` VARCHAR(50) DEFAULT 'cod',
  `payment_status` ENUM('pending', 'paid', 'failed', 'refunded') DEFAULT 'pending',
  `order_status` ENUM('placed', 'confirmed', 'preparing', 'ready', 'out_for_delivery', 'delivered', 'cancelled') DEFAULT 'placed',
  `coupon_id` INT DEFAULT NULL,
  `notes` TEXT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`restaurant_id`) REFERENCES `restaurants`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `order_items` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `order_id` INT NOT NULL,
  `food_item_id` INT NOT NULL,
  `quantity` INT NOT NULL,
  `price` DECIMAL(8,2) NOT NULL,
  `subtotal` DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`food_item_id`) REFERENCES `food_items`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `payments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `order_id` INT NOT NULL,
  `transaction_id` VARCHAR(100) NOT NULL UNIQUE,
  `razorpay_order_id` VARCHAR(100) DEFAULT '',
  `payment_method` VARCHAR(50) NOT NULL,
  `amount` DECIMAL(10,2) NOT NULL,
  `payment_status` ENUM('pending', 'paid', 'failed') DEFAULT 'paid',
  `payment_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `reviews` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `restaurant_id` INT NOT NULL,
  `order_id` INT DEFAULT NULL,
  `rating` INT NOT NULL,
  `comment` TEXT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`restaurant_id`) REFERENCES `restaurants`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `delivery_partners` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL UNIQUE,
  `vehicle_type` VARCHAR(50) DEFAULT 'Motorcycle',
  `vehicle_number` VARCHAR(50) DEFAULT 'GJ-01-AB-1234',
  `license_number` VARCHAR(50) DEFAULT 'DL-GJ2022001928',
  `is_available` TINYINT(1) DEFAULT 1,
  `current_lat` DECIMAL(10,7) DEFAULT 23.0225,
  `current_lng` DECIMAL(10,7) DEFAULT 72.5714,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `delivery_assignments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `order_id` INT NOT NULL UNIQUE,
  `partner_id` INT NOT NULL,
  `status` ENUM('assigned', 'picked_up', 'out_for_delivery', 'delivered', 'cancelled') DEFAULT 'assigned',
  `assigned_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `picked_at` DATETIME DEFAULT NULL,
  `delivered_at` DATETIME DEFAULT NULL,
  FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`partner_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `complaints` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT DEFAULT NULL,
  `name` VARCHAR(100) DEFAULT NULL,
  `email` VARCHAR(100) DEFAULT NULL,
  `order_id` INT DEFAULT NULL,
  `subject` VARCHAR(150) DEFAULT NULL,
  `message` TEXT DEFAULT NULL,
  `status` ENUM('open', 'in_progress', 'resolved') DEFAULT 'open',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `admin_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `admin_id` INT DEFAULT NULL,
  `action` VARCHAR(100) NOT NULL,
  `details` TEXT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def generate_database_sql():
    """Build database.sql with schema + seed inserts."""
    lines = [SQL_SCHEMA.strip(), "\n-- ========================================================", "-- SEED DATA INSERTS", "-- ========================================================\n"]

    # 1. Users
    lines.append("-- Users (Demo accounts)")
    for u in USERS:
        name = u[1].replace("'", "''")
        email = u[2]
        phone = u[3]
        role = u[4]
        addr = u[5].replace("'", "''")
        lines.append(f"INSERT INTO `users` (`id`, `name`, `email`, `phone`, `password_hash`, `role`, `address`, `status`) VALUES ({u[0]}, '{name}', '{email}', '{phone}', '{DEFAULT_PW_HASH}', '{role}', '{addr}', 'active');")
    lines.append("")

    # 2. Categories
    lines.append("-- Food Categories")
    for c in CATEGORIES:
        lines.append(f"INSERT INTO `food_categories` (`id`, `name`, `icon`, `image`, `sort_order`) VALUES ({c[0]}, '{c[1]}', '{c[2]}', '{c[3]}', {c[4]});")
    lines.append("")

    # 3. Restaurants
    lines.append("-- Restaurants")
    for r in RESTAURANTS:
        desc = r[3].replace("'", "''")
        name = r[2].replace("'", "''")
        cuisine = r[4].replace("'", "''")
        addr = r[5].replace("'", "''")
        lines.append(f"INSERT INTO `restaurants` (`id`, `owner_id`, `name`, `description`, `cuisine`, `address`, `phone`, `rating`, `delivery_time`, `delivery_fee`, `min_order`, `image`, `status`) VALUES ({r[0]}, {r[1]}, '{name}', '{desc}', '{cuisine}', '{addr}', '{r[6]}', {r[7]}, '{r[8]}', {r[9]}, {r[10]}, '{r[11]}', '{r[12]}');")
    lines.append("")

    # 4. Food Items
    lines.append("-- Food Items")
    for fi in FOOD_ITEMS:
        name = fi[3].replace("'", "''")
        desc = fi[4].replace("'", "''")
        lines.append(f"INSERT INTO `food_items` (`id`, `restaurant_id`, `category_id`, `name`, `description`, `price`, `image`, `veg_type`, `availability`, `rating`) VALUES ({fi[0]}, {fi[1]}, {fi[2]}, '{name}', '{desc}', {fi[5]}, '{fi[6]}', '{fi[7]}', {fi[8]}, {fi[9]});")
    lines.append("")

    # 5. Coupons
    lines.append("-- Coupons")
    for cp in COUPONS:
        desc = cp[2].replace("'", "''")
        max_d = cp[5] if cp[5] is not None else "NULL"
        lines.append(f"INSERT INTO `coupons` (`id`, `code`, `description`, `discount_type`, `discount_value`, `max_discount`, `min_order_amount`, `expiry_date`, `usage_limit`, `is_active`) VALUES ({cp[0]}, '{cp[1]}', '{desc}', '{cp[3]}', {cp[4]}, {max_d}, {cp[6]}, '{cp[7]}', {cp[8]}, {cp[9]});")
    lines.append("")

    # 6. Addresses
    lines.append("-- Addresses")
    for a in ADDRESSES:
        addr = a[3].replace("'", "''")
        lines.append(f"INSERT INTO `addresses` (`id`, `user_id`, `label`, `address`, `city`, `pincode`, `is_default`) VALUES ({a[0]}, {a[1]}, '{a[2]}', '{addr}', '{a[4]}', '{a[5]}', {a[6]});")
    lines.append("")

    # 7. Delivery Partners
    lines.append("-- Delivery Partners")
    for dp in DELIVERY_PARTNERS:
        lines.append(f"INSERT INTO `delivery_partners` (`id`, `user_id`, `vehicle_type`, `vehicle_number`, `license_number`, `is_available`) VALUES ({dp[0]}, {dp[1]}, '{dp[2]}', '{dp[3]}', '{dp[4]}', {dp[5]});")
    lines.append("")

    # 8. Reviews
    lines.append("-- Reviews")
    for rv in REVIEWS:
        comm = rv[5].replace("'", "''")
        ord_id = rv[3] if rv[3] is not None else "NULL"
        lines.append(f"INSERT INTO `reviews` (`id`, `user_id`, `restaurant_id`, `order_id`, `rating`, `comment`) VALUES ({rv[0]}, {rv[1]}, {rv[2]}, {ord_id}, {rv[4]}, '{comm}');")
    lines.append("")

    # 9. Orders
    lines.append("-- Demo Orders")
    for o in ORDERS:
        cid = o[12] if o[12] is not None else "NULL"
        notes = f"'{o[13]}'" if o[13] else "NULL"
        lines.append(f"INSERT INTO `orders` (`id`, `order_code`, `user_id`, `restaurant_id`, `address_id`, `total_amount`, `delivery_fee`, `discount`, `tax`, `payment_method`, `payment_status`, `order_status`, `coupon_id`, `notes`) VALUES ({o[0]}, '{o[1]}', {o[2]}, {o[3]}, {o[4]}, {o[5]}, {o[6]}, {o[7]}, {o[8]}, '{o[9]}', '{o[10]}', '{o[11]}', {cid}, {notes});")
    lines.append("")

    # 10. Order Items
    lines.append("-- Order Items")
    for oi in ORDER_ITEMS:
        lines.append(f"INSERT INTO `order_items` (`id`, `order_id`, `food_item_id`, `quantity`, `price`, `subtotal`) VALUES ({oi[0]}, {oi[1]}, {oi[2]}, {oi[3]}, {oi[4]}, {oi[5]});")
    lines.append("")

    # 11. Delivery Assignments
    lines.append("-- Delivery Assignments")
    for da in DELIVERY_ASSIGNMENTS:
        lines.append(f"INSERT INTO `delivery_assignments` (`id`, `order_id`, `partner_id`, `status`) VALUES ({da[0]}, {da[1]}, {da[2]}, '{da[3]}');")
    lines.append("")

    # 12. Payments
    lines.append("-- Payments")
    for py in PAYMENTS:
        lines.append(f"INSERT INTO `payments` (`id`, `order_id`, `transaction_id`, `razorpay_order_id`, `payment_method`, `amount`, `payment_status`) VALUES ({py[0]}, {py[1]}, '{py[2]}', '{py[3]}', '{py[4]}', {py[5]}, '{py[6]}');")
    lines.append("")

    content = "\n".join(lines)
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.sql")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated: {sql_path}")


def init_sqlite_db():
    """Initialize or safely upgrade local SQLite database."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "foody_hunters.db")
    if os.path.exists(db_path):
        import migrations
        conn = sqlite3.connect(db_path)
        migrations.migrate_sqlite(conn)
        conn.close()
        print(f"Safely upgraded existing SQLite database: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      phone TEXT,
      password_hash TEXT NOT NULL,
      role TEXT DEFAULT 'customer',
      address TEXT,
      status TEXT DEFAULT 'active',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE restaurants (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      owner_id INTEGER,
      name TEXT NOT NULL,
      description TEXT,
      cuisine TEXT NOT NULL,
      address TEXT NOT NULL,
      phone TEXT,
      rating REAL DEFAULT 4.5,
      delivery_time TEXT DEFAULT '30-40 min',
      delivery_fee REAL DEFAULT 40.00,
      min_order REAL DEFAULT 100.00,
      image TEXT,
      status TEXT DEFAULT 'approved',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (owner_id) REFERENCES users(id)
    );

    CREATE TABLE food_categories (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      icon TEXT DEFAULT '🍽️',
      image TEXT,
      sort_order INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE restaurant_categories (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      restaurant_id INTEGER NOT NULL,
      category_id INTEGER NOT NULL
    );

    CREATE TABLE food_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      restaurant_id INTEGER NOT NULL,
      category_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      description TEXT,
      price REAL NOT NULL,
      image TEXT,
      veg_type TEXT DEFAULT 'veg',
      availability INTEGER DEFAULT 1,
      rating REAL DEFAULT 4.5,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE cart (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      status TEXT DEFAULT 'active',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE cart_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      cart_id INTEGER NOT NULL,
      food_item_id INTEGER NOT NULL,
      quantity INTEGER DEFAULT 1,
      price REAL NOT NULL
    );

    CREATE TABLE addresses (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      label TEXT DEFAULT 'Home',
      address TEXT NOT NULL,
      city TEXT DEFAULT 'Ahmedabad',
      pincode TEXT DEFAULT '380001',
      is_default INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE coupons (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      code TEXT NOT NULL UNIQUE,
      description TEXT,
      discount_type TEXT DEFAULT 'percentage',
      discount_value REAL NOT NULL,
      max_discount REAL,
      min_order_amount REAL DEFAULT 0.00,
      expiry_date TEXT,
      usage_limit INTEGER DEFAULT 1000,
      is_active INTEGER DEFAULT 1,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_code TEXT NOT NULL UNIQUE,
      user_id INTEGER NOT NULL,
      restaurant_id INTEGER NOT NULL,
      address_id INTEGER,
      total_amount REAL NOT NULL,
      delivery_fee REAL DEFAULT 40.00,
      discount REAL DEFAULT 0.00,
      tax REAL DEFAULT 0.00,
      payment_method TEXT DEFAULT 'cod',
      payment_status TEXT DEFAULT 'pending',
      order_status TEXT DEFAULT 'placed',
      coupon_id INTEGER,
      notes TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE order_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL,
      food_item_id INTEGER NOT NULL,
      quantity INTEGER NOT NULL,
      price REAL NOT NULL,
      subtotal REAL NOT NULL
    );

    CREATE TABLE payments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL,
      transaction_id TEXT NOT NULL UNIQUE,
      razorpay_order_id TEXT DEFAULT '',
      payment_method TEXT NOT NULL,
      amount REAL NOT NULL,
      payment_status TEXT DEFAULT 'paid',
      payment_date DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE reviews (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      restaurant_id INTEGER NOT NULL,
      order_id INTEGER,
      rating INTEGER NOT NULL,
      comment TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE delivery_partners (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL UNIQUE,
      vehicle_type TEXT DEFAULT 'Motorcycle',
      vehicle_number TEXT DEFAULT 'GJ-01-AB-1234',
      license_number TEXT DEFAULT 'DL-GJ2022001928',
      is_available INTEGER DEFAULT 1,
      current_lat REAL DEFAULT 23.0225,
      current_lng REAL DEFAULT 72.5714,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE delivery_assignments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL UNIQUE,
      partner_id INTEGER NOT NULL,
      status TEXT DEFAULT 'assigned',
      assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      picked_at DATETIME,
      delivered_at DATETIME
    );

    CREATE TABLE complaints (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER,
      name TEXT,
      email TEXT,
      order_id INTEGER,
      subject TEXT,
      message TEXT,
      status TEXT DEFAULT 'open',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE admin_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      admin_id INTEGER,
      action TEXT NOT NULL,
      details TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Populate seed data
    for u in USERS:
        cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                    (u[0], u[1], u[2], u[3], DEFAULT_PW_HASH, u[4], u[5], "active"))

    for c in CATEGORIES:
        cur.execute("INSERT INTO food_categories VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)",
                    (c[0], c[1], c[2], c[3], c[4]))

    for r in RESTAURANTS:
        cur.execute("INSERT INTO restaurants VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                    (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12]))

    for fi in FOOD_ITEMS:
        cur.execute("INSERT INTO food_items VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                    (fi[0], fi[1], fi[2], fi[3], fi[4], fi[5], fi[6], fi[7], fi[8], fi[9]))

    for cp in COUPONS:
        cur.execute("INSERT INTO coupons VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                    (cp[0], cp[1], cp[2], cp[3], cp[4], cp[5], cp[6], cp[7], cp[8], cp[9]))

    for a in ADDRESSES:
        cur.execute("INSERT INTO addresses VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                    (a[0], a[1], a[2], a[3], a[4], a[5], a[6]))

    for dp in DELIVERY_PARTNERS:
        cur.execute("INSERT INTO delivery_partners VALUES (?,?,?,?,?,?,23.0225,72.5714,CURRENT_TIMESTAMP)",
                    (dp[0], dp[1], dp[2], dp[3], dp[4], dp[5]))

    for rv in REVIEWS:
        cur.execute("INSERT INTO reviews VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                    (rv[0], rv[1], rv[2], rv[3], rv[4], rv[5]))

    for o in ORDERS:
        cur.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                    (o[0], o[1], o[2], o[3], o[4], o[5], o[6], o[7], o[8], o[9], o[10], o[11], o[12], o[13]))

    for oi in ORDER_ITEMS:
        cur.execute("INSERT INTO order_items VALUES (?,?,?,?,?,?)",
                    (oi[0], oi[1], oi[2], oi[3], oi[4], oi[5]))

    for da in DELIVERY_ASSIGNMENTS:
        cur.execute("INSERT INTO delivery_assignments VALUES (?,?,?,?,CURRENT_TIMESTAMP,NULL,NULL)",
                    (da[0], da[1], da[2], da[3]))

    for py in PAYMENTS:
        cur.execute("INSERT INTO payments VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                    (py[0], py[1], py[2], py[3], py[4], py[5], py[6]))

    conn.commit()
    conn.close()
    print(f"Initialized SQLite database: {db_path}")


if __name__ == "__main__":
    generate_database_sql()
    init_sqlite_db()
    print("Database generation completed successfully!")
