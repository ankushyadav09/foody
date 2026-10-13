"""
generate_seed.py – Generates comprehensive seed data for FOODIE HUNTER:
- 19 standard food categories
- 55+ realistic restaurants in Mehsana, Gujarat across multiple localities with GPS coordinates
- 160+ delicious food items mapped to restaurants and categories
- Demo accounts for Admin, Customer, Restaurant Owner, Delivery Partner with password 'password123'
- Real addresses with Mehsana coordinates
- Delivery partners with vehicles and online availability
- Working coupons, reviews, sample orders, payments, assignments, and notifications
Outputs: database/seed.sql, database/sample_data.sql, and can apply directly to MySQL/SQLite.
"""

import sys
import os
import random
from werkzeug.security import generate_password_hash

PW_HASH = generate_password_hash("password123")

CATEGORIES = [
    (1, "Gujarati", "🥘", "https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?w=500&q=80", "Authentic traditional Gujarati thali, sweets and farsan", 1),
    (2, "Kathiyawadi", "🌶️", "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=500&q=80", "Spicy and rustic Saurashtra delicacies cooked in clay pots", 2),
    (3, "Punjabi", "🫓", "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&q=80", "Rich butter paneer, dal makhani, garlic naans and tandoori grills", 3),
    (4, "North Indian", "🍲", "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?w=500&q=80", "Aromatic gravies, curries and Mughlai platters", 4),
    (5, "South Indian", "🥞", "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=500&q=80", "Crispy dosas, fluffy idlis, medu vada and filter coffee", 5),
    (6, "Chinese", "🍜", "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=500&q=80", "Hakka noodles, manchurian, momos and sizzling fried rice", 6),
    (7, "Pizza", "🍕", "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=500&q=80", "Wood-fired and cheese-burst artisan pizzas", 7),
    (8, "Burger", "🍔", "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500&q=80", "Gourmet juicy veg and chicken burgers with seasoned fries", 8),
    (9, "Fast Food", "🍟", "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=500&q=80", "Quick street-style snacks, frankies and puff pastries", 9),
    (10, "Sandwich", "🥪", "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=500&q=80", "Cheesy grilled sandwiches and club subs", 10),
    (11, "Bakery", "🥐", "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500&q=80", "Fresh artisanal breads, puffs, cookies and pastries", 11),
    (12, "Biryani", "🍛", "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=500&q=80", "Royal dum biryani cooked with saffron and whole spices", 12),
    (13, "Rolls", "🌯", "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=500&q=80", "Crispy kathi rolls, paneer wraps and chicken frankies", 13),
    (14, "Cafe", "☕", "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=500&q=80", "Espresso, cold coffees, shakes and ambient snacks", 14),
    (15, "Snacks", "🥟", "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&q=80", "Samosa, kachori, dhokla, fafda and tea-time savories", 15),
    (16, "Desserts", "🍰", "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=500&q=80", "Cakes, pastries, waffles and traditional sweets", 16),
    (17, "Ice Cream", "🍨", "https://images.unsplash.com/photo-1560008581-09826d1de69e?w=500&q=80", "Natural fruit scoops, faloodas, sundaes and kulfis", 17),
    (18, "Beverages", "🧋", "https://images.unsplash.com/photo-1544145945-f90425340c7e?w=500&q=80", "Mocktails, fresh juices, spiced buttermilk and thick shakes", 18),
    (19, "Thali", "🍱", "https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?w=500&q=80", "Unlimited grand lunch and dinner thali spreads", 19),
]

# Core demo users
CORE_USERS = [
    # id, name, email, phone, role, gender, dob, address, city, state, pincode
    (1, "Raj Patel", "customer@foodiehunter.com", "9876543210", "customer", "male", "1998-05-14", "Flat 302, Radhe Residency, Radhanpur Road", "Mehsana", "Gujarat", "384002"),
    (2, "Chef Sanjeev Kumar", "restaurant@foodiehunter.com", "9823456789", "restaurant", "male", "1985-08-22", "Shop 12, Modhera Cross Road", "Mehsana", "Gujarat", "384002"),
    (3, "Vikram Singh", "delivery@foodiehunter.com", "9812345678", "delivery", "male", "1996-11-03", "14, Shivam Society, Nagalpur", "Mehsana", "Gujarat", "384002"),
    (4, "System Administrator", "admin@foodiehunter.com", "9898989898", "admin", "male", "1990-01-01", "Foodie Hunter Office, Highway Complex", "Mehsana", "Gujarat", "384002"),
    # Alternate emails for backward compatibility with existing tests
    (5, "Rajesh Shah", "customer@foodyhunters.com", "9876543211", "customer", "male", "1997-03-12", "A-102, Shivalik Park, Wide Road", "Mehsana", "Gujarat", "384001"),
    (6, "Kiran Dave", "restaurant@foodyhunters.com", "9823456780", "restaurant", "female", "1988-06-15", "Ground Floor, City Point, Radhanpur Road", "Mehsana", "Gujarat", "384002"),
    (7, "Arun Parmar", "delivery@foodyhunters.com", "9812345670", "delivery", "male", "1999-09-19", "Plot 45, Panchot By-Pass", "Mehsana", "Gujarat", "384002"),
    (8, "Head Admin", "admin@foodyhunters.com", "9898989890", "admin", "male", "1989-12-30", "Administrative Block, Para Tower", "Mehsana", "Gujarat", "384001"),
    # Additional customers
    (9, "Pooja Patel", "pooja.patel@gmail.com", "9825112233", "customer", "female", "2000-04-18", "B-201, Shreenath Apartment, Somnath Road", "Mehsana", "Gujarat", "384001"),
    (10, "Amit Joshi", "amit.joshi@gmail.com", "9825445566", "customer", "male", "1995-10-25", "15, Gokul Dham Society, Dediyasan", "Mehsana", "Gujarat", "384002"),
    # Additional riders
    (11, "Hardik Solanki", "hardik.delivery@gmail.com", "9879112233", "delivery", "male", "1998-02-14", "Near Toranwali Mata Temple, Pilaji Ganj", "Mehsana", "Gujarat", "384001"),
    (12, "Mahesh Vaghela", "mahesh.delivery@gmail.com", "9879445566", "delivery", "male", "1995-07-08", "Near Malgodown Station Road", "Mehsana", "Gujarat", "384001"),
]

# 52 Mehsana Restaurants (Realistic demo data across Mehsana locations)
MEHSANA_LOCALITIES = [
    ("Radhanpur Road", 23.5935, 72.3640),
    ("Modhera Road", 23.5850, 72.3580),
    ("Mehsana Highway", 23.6020, 72.3850),
    ("Nagalpur Area", 23.5780, 72.3750),
    ("Dediyasan GIDC", 23.6110, 72.3520),
    ("Somnath Road", 23.5890, 72.3720),
    ("Panchot By-Pass", 23.5680, 72.3880),
    ("Para Tower", 23.5980, 72.3700),
    ("Pilaji Ganj", 23.6010, 72.3680),
    ("Visnagar Link Road", 23.6150, 72.3920),
    ("Malgodown Road", 23.5920, 72.3790),
    ("City Center", 23.5950, 72.3740),
]

RESTAURANT_NAMES_AND_CUISINES = [
    (1, "The Grand Thakar Gujarati & Kathiyawadi", "Gujarati, Kathiyawadi, Thali", "Renowned for authentic rustic Kathiyawadi thali, bajra no rotlo, and kaju gathiya.", 4.9, 1),
    (2, "Mehsana Spice Garden & Banquet", "North Indian, Punjabi, Chinese", "Lavish multi-cuisine family diner offering rich curries and tandoori sizzlers.", 4.8, 2),
    (3, "Shree Khodiyar Kathiyawadi Dhaba", "Kathiyawadi, Gujarati, Thali", "Pure desi ghee preparations with Sev Tameta, Ringna Olo, and unlimited chaas.", 4.9, 1),
    (4, "Toran Dining Hall & Fast Food", "Gujarati, Thali, Snacks", "Heritage Gujarati culinary thali experience loved by generations in North Gujarat.", 4.7, 1),
    (5, "Woodland Pizza & Italian Bistro", "Pizza, Fast Food, Beverages", "Stone-baked Italian thin crust pizzas with loaded cheese burst options.", 4.6, 7),
    (6, "Shreeji Pav Bhaji & Pulao Center", "Fast Food, Snacks, Street Food", "Iconic Amul butter pav bhaji, tawa pulao, and grilled sandwiches.", 4.8, 9),
    (7, "Saffron Royal Multicuisine", "North Indian, Punjabi, Mughlai", "Grand family dining with paneer butter masala, rich biryanis and tandoor.", 4.7, 3),
    (8, "Honest Restaurant Mehsana Highway", "Fast Food, Gujarati, South Indian", "Famous for classic butter pav bhaji, crisp dosas, and quick highway meals.", 4.8, 9),
    (9, "Dosa Kingdom & South Corner", "South Indian, Fast Food, Beverages", "Over 50 types of crispy butter and cheese dosas, idlis, and filter coffee.", 4.7, 5),
    (10, "Urban Burger & Cafe Hub", "Burger, Fast Food, Cafe", "Gourmet juicy veg and crispy patties, loaded cheesy fries and thick shakes.", 4.6, 8),
    (11, "Surti Khaman & Fafda Sweets", "Snacks, Gujarati, Fast Food", "Piping hot fafda, jalebi, surti locho and nylon khaman made fresh daily.", 4.9, 15),
    (12, "Gopi Dining Hall & Thali", "Gujarati, Thali, Kathiyawadi", "Wholesome executive and unlimited Gujarati thali with puran poli and sweets.", 4.8, 1),
    (13, "Chatori Gali Street Bites", "Snacks, Fast Food, Rolls", "Famous street rolls, dahi puri, sev puri and spicy frankies.", 4.5, 9),
    (14, "Pizza Wings & More", "Pizza, Fast Food, Cafe", "Delicious 7-cheese pizzas, garlic breads and peri peri pasta bowls.", 4.6, 7),
    (15, "Madras Cafe Express", "South Indian, Beverages", "Authentic Mysore masala dosa, ghee podi idlis and hot degree filter coffee.", 4.8, 5),
    (16, "Pind Balluchi Punjabi Rasoi", "Punjabi, North Indian, Tandoor", "Smoky tandoori paneer, dal makhani, butter naan and refreshing lassi.", 4.7, 3),
    (17, "Dum Safar Biryani & Kebabs", "Biryani, North Indian, Rolls", "Aromatic long-grain Dum Biryani slow cooked in clay handis.", 4.7, 12),
    (18, "Tea Post & Desi Cafe", "Cafe, Snacks, Beverages", "Signature kulhad chai, puff varieties, bun muska and grilled sandwiches.", 4.6, 14),
    (19, "Havmor Ice Cream & Restaurant", "Ice Cream, Fast Food, Desserts", "Classic Chana Puri, pizzas, and rich exotic sundaes & ice creams.", 4.8, 17),
    (20, "Cafe Chocolicious", "Cafe, Desserts, Beverages", "Rich chocolate shakes, hot Belgian waffles and artisanal cold brews.", 4.7, 14),
    (21, "Wok In China Noodles & Rice", "Chinese, Fast Food, Asian", "Spicy Schezwan Hakka noodles, manchurian bowls and crispy spring rolls.", 4.5, 6),
    (22, "Shree Maruti Sandwich & Pizza", "Sandwich, Pizza, Fast Food", "Jumbo Bahubali grilled sandwiches loaded with cheese and spicy chutneys.", 4.7, 10),
    (23, "Radhe Dhokla & Farsan House", "Snacks, Gujarati, Fast Food", "Famous Live Dhokla, Idada, and crisp Kachori with sweet-tangy chutneys.", 4.8, 15),
    (24, "Kathiyawadi Chamunda Dining", "Kathiyawadi, Gujarati, Thali", "Homestyle Ringna Olo, Lasaniya Bataka and hot Bajra rotla with white butter.", 4.9, 2),
    (25, "The Belgian Waffle Co.", "Desserts, Bakery, Cafe", "Warm crispy waffles dusted with cinnamon and flooded with Belgian chocolate.", 4.8, 16),
    (26, "Subway Highway Hub", "Sandwich, Fast Food, Healthy", "Fresh salads, multigrain subs and toasted wraps customized your way.", 4.5, 10),
    (27, "Kwality Wall's Swirl's Sundaes", "Ice Cream, Desserts", "Colorful Cornettos, Feast bars, Cassata slices and magnum ice creams.", 4.6, 17),
    (28, "Bakers Basket & Cake Studio", "Bakery, Desserts, Cafe", "Freshly baked customized celebration cakes, pastries and butter cookies.", 4.7, 11),
    (29, "Sankalp Restaurant Highway", "South Indian, Thali", "Record-holding authentic South Indian delicacies, vadas, and rava dosas.", 4.8, 5),
    (30, "Moti Mahal Deluxe Mehsana", "North Indian, Punjabi, Mughlai", "Inventor of Butter Chicken recipes and legendary tandoori delicacies.", 4.7, 3),
    (31, "La Pino'z Pizza Radhanpur Road", "Pizza, Fast Food, Italian", "Giant monster slices, garlic cheese twists and creamy carbonara pasta.", 4.6, 7),
    (32, "Shambhu's Coffee Bar", "Cafe, Beverages, Snacks", "Frothy cold coffee, iced frappes, grilled subs and potato wedges.", 4.5, 14),
    (33, "Karnavati Dabeli & Vadapav", "Snacks, Fast Food", "Spicy butter grilled Kutchi dabelis, Mumbai vadapavs and fried chilies.", 4.8, 15),
    (34, "Jay Jalaram Khichdi Restaurant", "Gujarati, Kathiyawadi, Thali", "Over 20 wholesome fusion khichdi varieties served with kadhi and papad.", 4.9, 1),
    (35, "Tandoori Nights Barbeque", "North Indian, Biryani, Punjabi", "Sizzling paneer tikka platters, roomali roti, and dum mutton biryani.", 4.6, 3),
    (36, "Rolls Mania Express", "Rolls, Fast Food, Snacks", "Spicy Paneer Tikka Rolls, Aloo Schezwan Rolls and crunchy egg wraps.", 4.5, 13),
    (37, "The Chocolate Room Mehsana", "Cafe, Desserts, Beverages", "Chocolate fondues, death by chocolate sundaes and hot cocoa mugs.", 4.7, 14),
    (38, "Amul Ice Cream Lounge", "Ice Cream, Beverages, Desserts", "Traditional Kesar Pista kulfi, Rajbhog scoops and Amul ice cream shakes.", 4.8, 17),
    (39, "Jay Bhavani Vadapav & Bites", "Fast Food, Snacks, Sandwich", "Crisp golden potato vadas, cheese dabelis and masala grilled bread.", 4.7, 15),
    (40, "Dragon Wok & Dimsum House", "Chinese, Asian, Fast Food", "Translucent steamed momos, fiery chili garlic noodles and manchow soup.", 4.5, 6),
    (41, "Udupi Shree Krishna Grand", "South Indian, Fast Food", "Ghee roast paper masala dosa, onion uttapam and aromatic rasam rice.", 4.8, 5),
    (42, "Baskin Robbins Modhera Road", "Ice Cream, Desserts", "31 flavors of premium churned ice creams, sundaes and waffle cones.", 4.8, 17),
    (43, "Kathi Junction Mehsana", "Rolls, Fast Food, North Indian", "Kolkata style crisp flaky laccha paratha rolls with mint chutney.", 4.6, 13),
    (44, "Purohit Thali & Dining Hall", "Gujarati, Rajasthani, Thali", "Royal Marwari and Gujarati feast with dal baati churma and gatta curry.", 4.8, 19),
    (45, "Mehsana Dairy Sweet Parlour", "Snacks, Desserts, Gujarati", "Authentic Dudhsagar dairy peda, fresh shrikhand, basundi and rabdi.", 4.9, 16),
    (46, "Chai Sutta Bar Mehsana", "Cafe, Beverages, Snacks", "Flavored kulhad chai, chocolate tea, peri peri fries and maska bun.", 4.6, 14),
    (47, "Mahalaxmi Sweets & Farsan", "Snacks, Desserts, Bakery", "Crispy hot samosas, dal kachoris, mohanthal and pure ghee sweets.", 4.8, 15),
    (48, "The Yellow Chilli by Sanjeev Kapoor", "North Indian, Punjabi, Mughlai", "Masterchef signature recipes of Lalla Mussa Dal, Shaam Savera, and biryanis.", 4.9, 4),
    (49, "Mocha Cafe & Bar Mehsana", "Cafe, Italian, Fast Food", "Gourmet thin crust pizzas, paninis, creamy shakes and artisan cappuccinos.", 4.7, 14),
    (50, "Panchamrut Kathiyawadi Rasoi", "Kathiyawadi, Gujarati, Thali", "Traditional Chulha cooked Baingan Bharta, Lasan ni Chutney and fresh buttermilk.", 4.9, 2),
    (51, "Pizza Hut Mehsana Highway", "Pizza, Italian, Fast Food", "Pan pizzas loaded with mozzarella, pasta bowls and garlic bread sticks.", 4.6, 7),
    (52, "Burger King City Center", "Burger, Fast Food, Beverages", "Whopper burgers, crispy chicken royale, cheesy fries and thick shakes.", 4.6, 8),
]

# Food catalog templates (dish name, category_id, base price, is_veg, desc)
DISH_TEMPLATES = [
    # Gujarati & Kathiyawadi (Cat 1, 2, 19)
    ("Royal Gujarati Unlimited Thali", 1, 260.0, "veg", "Complete thali with 4 subzi, phulka roti, puran poli, dal, bhat, farsan and chaas."),
    ("Kathiyawadi Special Thali", 2, 280.0, "veg", "Ringna No Olo, Sev Tameta, Bajra No Rotlo with fresh white makhan and jaggery."),
    ("Ringna No Olo with Bajra Rotlo (2 pcs)", 2, 190.0, "veg", "Smoky roasted eggplant mash tempered with garlic and green chilies, served with millet flatbread."),
    ("Sev Tameta Nu Shaak", 2, 150.0, "veg", "Spicy and tangy tomato gravy topped with crispy chickpea sev."),
    ("Kaju Gathiya Shaak", 2, 210.0, "veg", "Rich Kathiyawadi curry made with fried gathiya, roasted cashews and aromatic gravy."),
    ("Lasaniya Bataka", 2, 160.0, "veg", "Baby potatoes simmered in fiery red garlic and chili masala."),
    ("Khaman Dhokla Platter", 15, 90.0, "veg", "Steamed spongy nylon khaman with mustard tempering, green chilies and mint chutney."),
    ("Surti Sev Khamani", 15, 110.0, "veg", "Crushed spiced chana dal sautéed in ghee, topped with crisp sev and pomegranate seeds."),
    ("Dal Baati Churma Thali", 19, 240.0, "veg", "Crisp baked wheat baatis soaked in desi ghee, spicy panchmel dal, and sweet churma."),
    ("Vaghirelo Rotlo with Curd", 2, 140.0, "veg", "Crushed bajra rotla tossed with buttermilk, garlic paste, mustard seeds and curry leaves."),
    ("Kesar Pista Shrikhand (250g)", 16, 130.0, "veg", "Creamy strained yogurt delicacy enriched with saffron strands, cardamom and pistachios."),
    ("Masala Chaas Matka", 18, 40.0, "veg", "Chilled traditional spiced buttermilk with roasted jeera, rock salt and fresh mint."),

    # Punjabi & North Indian (Cat 3, 4)
    ("Paneer Butter Masala", 3, 240.0, "veg", "Tender malai paneer cubes simmered in velvety tomato, butter and cashew cream gravy."),
    ("Dal Makhani (16hr Slow Cooked)", 3, 210.0, "veg", "Whole black lentils slow simmered overnight with butter, cream and gentle spices."),
    ("Kadhai Paneer Special", 3, 230.0, "veg", "Fresh cottage cheese, crisp bell peppers and onions tossed in freshly ground kadhai masala."),
    ("Tandoori Butter Naan (2 pcs)", 3, 70.0, "veg", "Oven baked leavened flatbread brushed with garlic and melted butter."),
    ("Amritsari Kulcha with Chole", 3, 190.0, "veg", "Flaky layered stuffed bread baked in clay tandoor, served with spicy chickpea curry."),
    ("Butter Chicken (Murgh Makhani)", 4, 310.0, "non_veg", "Smoked tandoori chicken cooked in rich velvety tomato, cream and makhani butter gravy."),
    ("Chicken Tikka Masala", 4, 290.0, "non_veg", "Charcoal roasted spiced chicken morsels simmered in thick onion-tomato gravy."),
    ("Mutton Rogan Josh", 4, 380.0, "non_veg", "Kashmiri delicacy of tender mutton cooked with aromatic whole spices and ratan jot."),
    ("Tandoori Paneer Tikka (6 pcs)", 3, 220.0, "veg", "Charred cottage cheese cubes marinated in spiced yogurt and kasoori methi."),
    ("Murgh Malai Tikka (6 pcs)", 4, 280.0, "non_veg", "Melt-in-mouth chicken chunks marinated in cream, cheese and green cardamom."),

    # South Indian (Cat 5)
    ("Mysore Masala Dosa", 5, 140.0, "veg", "Crisp golden crepe smeared with spicy red garlic chutney and stuffed with potato masala."),
    ("Cheese Burst Paper Dosa", 5, 180.0, "veg", "Extra large crispy paper thin dosa flooded with molten Amul cheese."),
    ("Steamed Ghee Podi Idli (4 pcs)", 5, 120.0, "veg", "Fluffy mini steamed rice cakes tossed in aromatic gunpowder podi spice and desi ghee."),
    ("Medu Vada Sambar (2 pcs)", 5, 90.0, "veg", "Crispy lentil fritters served with piping hot drumstick sambar and coconut chutney."),
    ("Rava Onion Masala Dosa", 5, 150.0, "veg", "Crunchy semolina crepe sprinkled with chopped onions, green chilies and cumin."),
    ("Degree Filter Coffee", 18, 60.0, "veg", "Traditional South Indian chicory drip coffee frothed with boiling whole milk."),

    # Pizza, Burger, Sandwich, Fast Food (Cat 7, 8, 9, 10)
    ("Margherita Classic Pizza", 7, 240.0, "veg", "Classic San Marzano tomato puree, fresh mozzarella fior di latte and basil leaves."),
    ("Farmhouse Veggie Overload Pizza", 7, 290.0, "veg", "Loaded with crisp bell peppers, red onions, mushrooms, black olives and sweet corn."),
    ("Peri Peri Paneer Supreme Pizza", 7, 330.0, "veg", "Spicy marinated cottage cheese, red paprika, jalapeños and peri peri mayo swirl."),
    ("Smoked BBQ Chicken Pizza", 7, 360.0, "non_veg", "Tender smoked chicken cubes tossed in smoky hickory BBQ glaze and mozzarella."),
    ("Cheesy Garlic Breadsticks", 7, 140.0, "veg", "Fresh baked breadsticks stuffed with molten cheese and Italian herbs."),
    ("Ultimate Crispy Paneer Burger", 8, 170.0, "veg", "Crunchy breaded cottage cheese patty with spicy chipotle mayo and cheddar slice."),
    ("Smoky Crunch Chicken Burger", 8, 210.0, "non_veg", "Crispy fried chicken breast fillet with smokey BBQ sauce and crunchy pickles."),
    ("Aloo Tikki Street Crunch Burger", 8, 99.0, "veg", "Spiced golden potato patty, tangy mint mayonnaise, sliced onions and fresh tomatoes."),
    ("Peri Peri Loaded Cheese Fries", 9, 150.0, "veg", "Golden crispy french fries dusted with peri peri spice and smothered in melted cheese sauce."),
    ("Bahubali Jumbo Grilled Sandwich", 10, 190.0, "veg", "Triple layer jumbo toast stuffed with spiced potatoes, cheese, veggies and green chutney."),
    ("Chocolate Cheese Grilled Sandwich", 10, 150.0, "veg", "Decadent dessert sandwich loaded with chocolate fudge and sweet mozzarella."),
    ("Amul Butter Pav Bhaji (2 Pav)", 9, 140.0, "veg", "Mashed spiced vegetable curry cooked with generous Amul butter, served with roasted pav."),
    ("Cheese Butter Masala Pav", 9, 120.0, "veg", "Soft pav breads tossed on tawa in spicy tomato gravy and covered with grated cheese."),

    # Chinese & Momos (Cat 6)
    ("Veg Hakka Noodles", 6, 160.0, "veg", "Wok tossed julienne vegetables and noodles in sesame oil, light soy and white pepper."),
    ("Veg Manchurian Gravy", 6, 170.0, "veg", "Crisp vegetable dumplings simmered in dark, glossy, pungent garlic and ginger broth."),
    ("Schezwan Chicken Fried Rice", 6, 230.0, "non_veg", "Wok-fried jasmine rice tossed with chicken chunks and spicy house Schezwan paste."),
    ("Steamed Dimsum Momos (6 pcs)", 6, 130.0, "veg", "Translucent steamed dumplings stuffed with finely minced vegetables and chili dip."),
    ("Crispy Honey Chilli Potatoes", 6, 150.0, "veg", "Double fried crispy potato batons glazed in honey, toasted sesame seeds and chili sauce."),

    # Biryani & Rolls (Cat 12, 13)
    ("Dum Hyderabadi Chicken Biryani", 12, 290.0, "non_veg", "Aromatic long grain basmati rice and marinated chicken slow cooked in sealed handi."),
    ("Shahi Veg Dum Biryani", 12, 230.0, "veg", "Garden fresh vegetables, paneer cubes and golden fried onions layered with saffron rice."),
    ("Royal Mutton Dum Biryani", 12, 380.0, "non_veg", "Tender mutton cuts slow cooked with basmati rice, mint, rose water and spices."),
    ("Paneer Tikka Kathi Roll", 13, 160.0, "veg", "Smoky charred paneer cubes rolled in crisp laccha paratha with mint mayonnaise."),
    ("Chicken Schezwan Frankie", 13, 190.0, "non_veg", "Spiced shredded chicken, crunchy onions and Schezwan sauce wrapped in grilled paratha."),

    # Desserts, Bakery, Ice Cream & Beverages (Cat 11, 14, 16, 17, 18)
    ("Belgian Chocolate Waffle", 16, 180.0, "veg", "Warm golden waffle topped with melted dark Belgian chocolate and chocolate drops."),
    ("Sizzling Walnut Brownie with Gelato", 16, 160.0, "veg", "Fudgy brownie on hot skillet served with rich vanilla ice cream and chocolate syrup."),
    ("New York Baked Cheesecake Slice", 16, 210.0, "veg", "Dense and creamy classic cheesecake on crunchy graham cracker base."),
    ("Gulab Jamun with Rabdi (2 pcs)", 16, 110.0, "veg", "Warm soft mawa dumplings soaked in cardamom sugar syrup, served with thickened rabdi."),
    ("Royal Kesar Pista Falooda", 17, 150.0, "veg", "Chilled rose milk layered with sabja seeds, falooda vermicelli, kulfi and dry fruits."),
    ("Exotic Rajbhog Ice Cream Scoop", 17, 80.0, "veg", "Creamy traditional milk ice cream infused with real saffron, almonds and cashews."),
    ("Belgian Dark Chocolate Thick Shake", 18, 140.0, "veg", "Dense blended milkshake made with rich dark chocolate fudge and ice cream."),
    ("Oreo Overload Cold Coffee", 14, 130.0, "veg", "Chilled brewed espresso blended with vanilla ice cream and crushed crunchy Oreos."),
    ("Fresh Mint Lemon Mojito", 18, 100.0, "veg", "Muddled fresh mint leaves, lemon wedges, cane sugar and chilled sparkling soda."),
    ("Kulhad Masala Special Chai", 14, 40.0, "veg", "Aromatic milk tea brewed with crushed ginger, green cardamom and cloves in earthen cup."),
]


def esc(val):
    if val is None:
        return ""
    return str(val).replace("'", "''")


def generate_seed_data():
    """Generates SQL seed data and returns statements dictionary."""
    statements = []

    # 1. Users
    for u in CORE_USERS:
        # id, name, email, phone, role, gender, dob, address, city, state, pincode
        sql = (
            f"INSERT INTO `users` (`id`, `name`, `email`, `phone`, `password_hash`, `role`, `gender`, `dob`, `address`, `city`, `state`, `pincode`, `status`) "
            f"VALUES ({u[0]}, '{esc(u[1])}', '{esc(u[2])}', '{esc(u[3])}', '{PW_HASH}', '{u[4]}', '{u[5]}', '{u[6]}', '{esc(u[7])}', '{esc(u[8])}', '{esc(u[9])}', '{esc(u[10])}', 'active') "
            f"ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `role`=VALUES(`role`);"
        )
        statements.append(sql)

    # 2. Food Categories
    for c in CATEGORIES:
        sql = (
            f"INSERT INTO `food_categories` (`id`, `name`, `icon`, `image`, `description`, `sort_order`, `is_active`) "
            f"VALUES ({c[0]}, '{esc(c[1])}', '{esc(c[2])}', '{esc(c[3])}', '{esc(c[4])}', {c[5]}, 1) "
            f"ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `icon`=VALUES(`icon`);"
        )
        statements.append(sql)

    # 3. Restaurants (52 restaurants in Mehsana)
    food_id_counter = 1
    food_statements = []
    rest_cat_statements = []

    for idx, r in enumerate(RESTAURANT_NAMES_AND_CUISINES, 1):
        loc = MEHSANA_LOCALITIES[(idx - 1) % len(MEHSANA_LOCALITIES)]
        area = loc[0]
        lat = loc[1] + ((idx % 7) - 3) * 0.0012
        lng = loc[2] + (((idx * 3) % 7) - 3) * 0.0014
        
        owner_id = 2 if idx % 2 == 1 else 6
        img_url = CATEGORIES[(r[5] - 1) % len(CATEGORIES)][3]

        sql = (
            f"INSERT INTO `restaurants` (`id`, `owner_id`, `name`, `description`, `cuisine`, `address`, `area`, `city`, `state`, `pincode`, `phone`, `email`, `rating`, `total_ratings`, `delivery_time`, `delivery_fee`, `min_order`, `open_time`, `close_time`, `image`, `latitude`, `longitude`, `verification_status`, `status`, `is_open`) "
            f"VALUES ({r[0]}, {owner_id}, '{esc(r[1])}', '{esc(r[3])}', '{esc(r[2])}', 'Shop {idx*3}, Near {esc(area)}, Mehsana', '{esc(area)}', 'Mehsana', 'Gujarat', '384002', '02762-2{idx+10:04d}', 'restaurant{idx}@foodiehunter.com', {r[4]}, {random.randint(45, 380)}, '{random.choice(['20-30 min', '25-35 min', '30-40 min'])}', {random.choice([30.0, 35.0, 40.0])}, {random.choice([100.0, 150.0, 200.0])}, '09:00', '23:00', '{esc(img_url)}', {lat:.7f}, {lng:.7f}, 'approved', 'active', 1) "
            f"ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `latitude`=VALUES(`latitude`), `longitude`=VALUES(`longitude`), `area`=VALUES(`area`);"
        )
        statements.append(sql)

        primary_cat_id = r[5]
        rest_cat_statements.append(
            f"INSERT IGNORE INTO `restaurant_categories` (`restaurant_id`, `category_id`) VALUES ({r[0]}, {primary_cat_id});"
        )

        matching_dishes = [d for d in DISH_TEMPLATES if d[1] == primary_cat_id]
        if len(matching_dishes) < 3:
            matching_dishes += [d for d in DISH_TEMPLATES if d not in matching_dishes][:4]

        selected_dishes = matching_dishes[:3]
        for dish in selected_dishes:
            price = dish[2]
            discount = 10.0 if (food_id_counter % 3 == 0) else 0.0
            final_price = price - (price * discount / 100.0)
            is_bestseller = 1 if (food_id_counter % 4 == 0) else 0
            
            food_sql = (
                f"INSERT INTO `food_items` (`id`, `restaurant_id`, `category_id`, `name`, `description`, `price`, `discount`, `final_price`, `image`, `veg_type`, `preparation_time`, `availability`, `is_bestseller`, `rating`, `total_ratings`) "
                f"VALUES ({food_id_counter}, {r[0]}, {dish[1]}, '{esc(dish[0])}', '{esc(dish[4])}', {price:.2f}, {discount:.2f}, {final_price:.2f}, '{esc(img_url)}', '{dish[3]}', {random.choice([15, 20, 25])}, 1, {is_bestseller}, {random.choice([4.5, 4.7, 4.8, 4.9])}, {random.randint(15, 120)}) "
                f"ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `final_price`=VALUES(`final_price`);"
            )
            food_statements.append(food_sql)
            food_id_counter += 1

    statements.extend(rest_cat_statements)
    statements.extend(food_statements)

    # 4. Addresses
    addresses = [
        (1, 1, "Home", "Flat 302, Radhe Residency, Behind Radhe Shopping Mall", "Radhanpur Road", "Mehsana", "Gujarat", "384002", 23.5938, 72.3645, 1),
        (2, 1, "Work", "2nd Floor, IT Hub, Highway Road", "Mehsana Highway", "Mehsana", "Gujarat", "384002", 23.6015, 72.3840, 0),
        (3, 1, "Other", "House 14, Somnath Bunglows", "Somnath Road", "Mehsana", "Gujarat", "384001", 23.5892, 72.3718, 0),
        (4, 5, "Home", "A-102, Shivalik Park, Wide Road", "Nagalpur Area", "Mehsana", "Gujarat", "384002", 23.5785, 72.3755, 1),
        (5, 9, "Home", "B-201, Shreenath Apartment", "Somnath Road", "Mehsana", "Gujarat", "384001", 23.5888, 72.3725, 1),
    ]
    for a in addresses:
        sql = (
            f"INSERT INTO `addresses` (`id`, `user_id`, `label`, `address`, `area`, `city`, `state`, `pincode`, `latitude`, `longitude`, `is_default`) "
            f"VALUES ({a[0]}, {a[1]}, '{esc(a[2])}', '{esc(a[3])}', '{esc(a[4])}', '{esc(a[5])}', '{esc(a[6])}', '{esc(a[7])}', {a[8]:.7f}, {a[9]:.7f}, {a[10]}) "
            f"ON DUPLICATE KEY UPDATE `address`=VALUES(`address`), `latitude`=VALUES(`latitude`), `longitude`=VALUES(`longitude`);"
        )
        statements.append(sql)

    # 5. Delivery Partners
    couriers = [
        (1, 3, "Motorcycle", "GJ-02-EE-4521", "DL-GJ02-2022-87654", 1, 1, 23.5920, 72.3660, 48, 2400.0),
        (2, 7, "Scooter", "GJ-02-AB-9876", "DL-GJ02-2021-12345", 1, 1, 23.5860, 72.3600, 32, 1600.0),
        (3, 11, "Electric Bike", "GJ-02-EV-1122", "DL-GJ02-2023-99887", 1, 1, 23.6010, 72.3830, 25, 1250.0),
        (4, 12, "Motorcycle", "GJ-02-KL-3344", "DL-GJ02-2020-55443", 1, 0, 23.5790, 72.3740, 19, 950.0),
    ]
    for cp in couriers:
        sql = (
            f"INSERT INTO `delivery_partners` (`id`, `user_id`, `vehicle_type`, `vehicle_number`, `license_number`, `is_available`, `is_online`, `current_lat`, `current_lng`, `total_deliveries`, `total_earnings`) "
            f"VALUES ({cp[0]}, {cp[1]}, '{esc(cp[2])}', '{esc(cp[3])}', '{esc(cp[4])}', {cp[5]}, {cp[6]}, {cp[7]:.7f}, {cp[8]:.7f}, {cp[9]}, {cp[10]:.2f}) "
            f"ON DUPLICATE KEY UPDATE `vehicle_number`=VALUES(`vehicle_number`), `is_online`=VALUES(`is_online`), `current_lat`=VALUES(`current_lat`), `current_lng`=VALUES(`current_lng`);"
        )
        statements.append(sql)

    # 6. Coupons
    coupons = [
        (1, "WELCOME50", "Flat 50% discount on first meal order up to ₹100", "percentage", 50.0, 100.0, 149.0, "2027-12-31", 1000, 1),
        (2, "MEHSANA50", "Mehsana Special: Flat ₹50 off on orders above ₹249", "fixed", 50.0, 50.0, 249.0, "2027-12-31", 1000, 1),
        (3, "FOOD20", "20% off on all restaurants above ₹299", "percentage", 20.0, 120.0, 299.0, "2027-12-31", 1000, 1),
        (4, "HUNTER10", "Flat 10% discount on any meal without minimum order", "percentage", 10.0, 80.0, 99.0, "2027-12-31", 1000, 1),
        (5, "FLAT100", "Special Super Saver: Flat ₹100 discount on orders above ₹499", "fixed", 100.0, 100.0, 499.0, "2027-12-31", 1000, 1),
    ]
    for cp in coupons:
        sql = (
            f"INSERT INTO `coupons` (`id`, `code`, `description`, `discount_type`, `discount_value`, `max_discount`, `min_order_amount`, `expiry_date`, `usage_limit`, `is_active`) "
            f"VALUES ({cp[0]}, '{esc(cp[1])}', '{esc(cp[2])}', '{cp[3]}', {cp[4]:.2f}, {cp[5]:.2f}, {cp[6]:.2f}, '{cp[7]}', {cp[8]}, {cp[9]}) "
            f"ON DUPLICATE KEY UPDATE `code`=VALUES(`code`), `discount_value`=VALUES(`discount_value`);"
        )
        statements.append(sql)

    # 7. Sample Orders
    orders = [
        (1, "FH-2026-000001", 1, 1, 1, "Flat 302, Radhe Residency, Radhanpur Road, Mehsana", 23.5938, 72.3645, 520.0, 35.0, 50.0, 25.0, "demo_upi", "paid", "delivered", 1, "Please pack extra jaggery and white butter."),
        (2, "FH-2026-000002", 1, 5, 1, "Flat 302, Radhe Residency, Radhanpur Road, Mehsana", 23.5938, 72.3645, 380.0, 30.0, 0.0, 18.0, "cod", "pending", "out_for_delivery", None, "Ring bell twice, leave at door if unreachable."),
        (3, "FH-2026-000003", 5, 2, 4, "A-102, Shivalik Park, Wide Road, Mehsana", 23.5785, 72.3755, 450.0, 40.0, 45.0, 20.0, "demo_card", "paid", "preparing", 3, "Make curries medium spicy."),
    ]
    for o in orders:
        c_id = f"{o[15]}" if o[15] is not None else "NULL"
        sql = (
            f"INSERT INTO `orders` (`id`, `order_code`, `user_id`, `restaurant_id`, `address_id`, `delivery_address`, `customer_lat`, `customer_lng`, `total_amount`, `delivery_fee`, `discount`, `tax`, `payment_method`, `payment_status`, `order_status`, `coupon_id`, `notes`) "
            f"VALUES ({o[0]}, '{o[1]}', {o[2]}, {o[3]}, {o[4]}, '{esc(o[5])}', {o[6]:.7f}, {o[7]:.7f}, {o[8]:.2f}, {o[9]:.2f}, {o[10]:.2f}, {o[11]:.2f}, '{o[12]}', '{o[13]}', '{o[14]}', {c_id}, '{esc(o[16])}') "
            f"ON DUPLICATE KEY UPDATE `order_status`=VALUES(`order_status`), `payment_status`=VALUES(`payment_status`);"
        )
        statements.append(sql)

    # 8. Order Items
    order_items = [
        (1, 1, 1, "Royal Gujarati Unlimited Thali", 2, 260.0, 520.0),
        (2, 2, 13, "Margherita Classic Pizza", 1, 240.0, 240.0),
        (3, 2, 17, "Cheesy Garlic Breadsticks", 1, 140.0, 140.0),
        (4, 3, 5, "Paneer Butter Masala", 1, 240.0, 240.0),
        (5, 3, 8, "Tandoori Butter Naan (2 pcs)", 3, 70.0, 210.0),
    ]
    for oi in order_items:
        sql = (
            f"INSERT INTO `order_items` (`id`, `order_id`, `food_item_id`, `item_name`, `quantity`, `price`, `subtotal`) "
            f"VALUES ({oi[0]}, {oi[1]}, {oi[2]}, '{esc(oi[3])}', {oi[4]}, {oi[5]:.2f}, {oi[6]:.2f}) "
            f"ON DUPLICATE KEY UPDATE `quantity`=VALUES(`quantity`);"
        )
        statements.append(sql)

    # 9. Payments
    payments = [
        (1, 1, "TXN-2026-0001", "demo_upi", 520.0, "paid"),
        (2, 3, "TXN-2026-0003", "demo_card", 450.0, "paid"),
    ]
    for p in payments:
        sql = (
            f"INSERT INTO `payments` (`id`, `order_id`, `transaction_id`, `payment_method`, `amount`, `payment_status`) "
            f"VALUES ({p[0]}, {p[1]}, '{p[2]}', '{p[3]}', {p[4]:.2f}, '{p[5]}') "
            f"ON DUPLICATE KEY UPDATE `payment_status`=VALUES(`payment_status`);"
        )
        statements.append(sql)

    # 10. Delivery Assignments
    assignments = [
        (1, 1, 3, "delivered"),
        (2, 2, 3, "out_for_delivery"),
        (3, 3, 7, "assigned"),
    ]
    for da in assignments:
        sql = (
            f"INSERT INTO `delivery_assignments` (`id`, `order_id`, `partner_id`, `status`) "
            f"VALUES ({da[0]}, {da[1]}, {da[2]}, '{da[3]}') "
            f"ON DUPLICATE KEY UPDATE `status`=VALUES(`status`);"
        )
        statements.append(sql)

    # 11. Delivery Locations
    locations = [
        (1, 3, 2, 23.5930, 72.3635),
        (2, 3, 2, 23.5933, 72.3638),
        (3, 3, 2, 23.5935, 72.3641),
    ]
    for loc in locations:
        sql = (
            f"INSERT INTO `delivery_locations` (`id`, `delivery_partner_id`, `order_id`, `latitude`, `longitude`) "
            f"VALUES ({loc[0]}, {loc[1]}, {loc[2]}, {loc[3]:.7f}, {loc[4]:.7f}) "
            f"ON DUPLICATE KEY UPDATE `latitude`=VALUES(`latitude`);"
        )
        statements.append(sql)

    # 12. Reviews
    reviews = [
        (1, 1, 1, 1, 5, "Best Gujarati & Kathiyawadi thali in Mehsana! The Ringna No Olo and Bajra Rotlo were extraordinary. Delivered hot and fresh!"),
        (2, 5, 2, None, 5, "Amazing North Indian food, rich paneer butter masala and garlic naans were perfect. Great packaging."),
        (3, 9, 5, None, 4, "Wood-fired crust was crispy and cheese was plentiful. Fast delivery within 25 minutes."),
    ]
    for rev in reviews:
        ord_id = f"{rev[3]}" if rev[3] is not None else "NULL"
        sql = (
            f"INSERT INTO `reviews` (`id`, `user_id`, `restaurant_id`, `order_id`, `rating`, `comment`) "
            f"VALUES ({rev[0]}, {rev[1]}, {rev[2]}, {ord_id}, {rev[4]}, '{esc(rev[5])}') "
            f"ON DUPLICATE KEY UPDATE `rating`=VALUES(`rating`);"
        )
        statements.append(sql)

    # 13. Favorites
    favorites = [
        (1, 1, "restaurant", 1),
        (2, 1, "restaurant", 5),
        (3, 1, "food", 1),
    ]
    for fav in favorites:
        sql = (
            f"INSERT IGNORE INTO `favorites` (`id`, `user_id`, `item_type`, `item_id`) "
            f"VALUES ({fav[0]}, {fav[1]}, '{fav[2]}', {fav[3]});"
        )
        statements.append(sql)

    # 14. Notifications
    notifications = [
        (1, 1, "customer", "Order Confirmed!", "Your order #FH-2026-000002 has been confirmed by Woodland Pizza.", "/customer/track/2"),
        (2, 1, "customer", "Welcome to Foodie Hunter", "Enjoy ₹100 off on your first order using code WELCOME50!", "/restaurants"),
        (3, 2, "restaurant", "New Order Received!", "You have received order #FH-2026-000003 for 4 items.", "/restaurant/orders"),
        (4, 3, "delivery", "Delivery Assigned", "You are assigned order #FH-2026-000002. Please pick up promptly.", "/delivery/orders"),
    ]
    for notif in notifications:
        sql = (
            f"INSERT INTO `notifications` (`id`, `user_id`, `role`, `title`, `message`, `link`, `is_read`) "
            f"VALUES ({notif[0]}, {notif[1]}, '{notif[2]}', '{esc(notif[3])}', '{esc(notif[4])}', '{esc(notif[5])}', 0) "
            f"ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);"
        )
        statements.append(sql)

    return statements



def write_sql_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(base_dir, 'database')
    os.makedirs(db_dir, exist_ok=True)

    statements = generate_seed_data()
    seed_sql_content = "-- FOODIE HUNTER: Complete Seed Data (52 Mehsana Restaurants, 150+ Food Items, Demo Users)\n"
    seed_sql_content += "USE `foody_hunters`;\n\n"
    seed_sql_content += "\n".join(statements) + "\n"

    # Write database/seed.sql
    seed_path = os.path.join(db_dir, 'seed.sql')
    with open(seed_path, 'w', encoding='utf-8') as f:
        f.write(seed_sql_content)
    print(f"[OK] Generated {seed_path} ({len(statements)} statements)")

    # Write database/sample_data.sql (identical complete seed set for academic submission)
    sample_path = os.path.join(db_dir, 'sample_data.sql')
    with open(sample_path, 'w', encoding='utf-8') as f:
        f.write(seed_sql_content)
    print(f"[OK] Generated {sample_path}")

    # Also keep root database.sql updated as combined schema + seed for simple one-click import
    schema_path = os.path.join(db_dir, 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_content = f.read()

    combined_path = os.path.join(base_dir, 'database.sql')
    with open(combined_path, 'w', encoding='utf-8') as f:
        f.write(schema_content + "\n\n" + seed_sql_content)
    print(f"[OK] Generated combined root {combined_path}")


def apply_to_databases():
    """Apply schema and seed directly to MySQL and SQLite."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(base_dir, 'database')
    schema_path = os.path.join(db_dir, 'schema.sql')
    seed_path = os.path.join(db_dir, 'seed.sql')

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    with open(seed_path, 'r', encoding='utf-8') as f:
        seed_sql = f.read()

    # 1. Apply to MySQL
    try:
        import mysql.connector
        from config import Config
        print("[INFO] Connecting to MySQL...")
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT
        )
        cursor = conn.cursor()
        
        # Execute schema statements
        print("[INFO] Applying Schema to MySQL...")
        for stmt in schema_sql.split(';'):
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)
        conn.commit()

        # Execute seed statements
        print("[INFO] Applying Seed Data to MySQL...")
        for stmt in seed_sql.split(';'):
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)
        conn.commit()

        cursor.close()
        conn.close()
        print("[SUCCESS] MySQL database foody_hunters successfully initialized with 52 Mehsana restaurants & 150+ foods!")
    except Exception as e:
        print(f"[WARNING] MySQL import notice: {e}")

    # 2. Also initialize SQLite foody_hunters.db for complete offline resilience
    try:
        import sqlite3
        sqlite_path = os.path.join(base_dir, 'foody_hunters.db')
        print(f"[INFO] Initializing SQLite database at {sqlite_path}...")
        from setup_db import init_sqlite_db
        init_sqlite_db()
        print("[SUCCESS] SQLite database foody_hunters.db initialized successfully!")
    except Exception as e:
        print(f"[NOTE] SQLite setup notice: {e}")


if __name__ == '__main__':
    write_sql_files()
    apply_to_databases()
