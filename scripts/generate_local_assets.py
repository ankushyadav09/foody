"""
generate_local_assets.py – Creates curated, high-fidelity local vector illustrations
for restaurants and food categories/items to guarantee 100% offline reliability
and distinct visual identities for every restaurant and dish.
"""

import os

RESTAURANTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'images', 'restaurants')
FOODS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'images', 'foods')

os.makedirs(RESTAURANTS_DIR, exist_ok=True)
os.makedirs(FOODS_DIR, exist_ok=True)

RESTAURANT_THEMES = [
    ('rest_1.svg', 'The Grand Thakar', 'Gujarati & Kathiyawadi Thali', '#FF5722', '#E64A19', '🥘', 'Royal Gujarati Thali'),
    ('rest_2.svg', 'Mehsana Spice Garden', 'North Indian & Mughlai Curries', '#3F51B5', '#1A237E', '🍛', 'North Indian Rasoi'),
    ('rest_3.svg', 'Woodland Pizza Bistro', 'Wood-fired Pizza & Pasta', '#D32F2F', '#B71C1C', '🍕', 'Italian Pizza & Bistro'),
    ('rest_4.svg', 'Dosa Kingdom', 'Authentic South Indian & Filter Coffee', '#388E3C', '#1B5E20', '🥞', 'Crispy Masala Dosa'),
    ('rest_5.svg', 'Urban Burger & Fries Hub', 'Gourmet Burgers, Shakes & Bites', '#FFA000', '#FF6F00', '🍔', 'Smash Burgers & Shakes'),
    ('rest_6.svg', 'Dum Safar Biryani', 'Hyderabadi & Awadhi Dum Biryani', '#7B1FA2', '#4A148C', '🍲', 'Handi Dum Biryani'),
    ('rest_7.svg', 'Dragon Wok Express', 'Hakka Noodles, Manchurian & Dimsum', '#C2185B', '#880E4F', '🍜', 'Asian Noodles & Dimsum'),
    ('rest_8.svg', 'Cafe Chocolicious', 'Belgian Waffles & Cold Brew Coffee', '#5D4037', '#3E2723', '☕', 'Artisan Coffee & Desserts'),
    ('rest_9.svg', 'Shreeji Pav Bhaji & Pulao', 'Mumbai Style Pav Bhaji & Street Food', '#E65100', '#BF360C', '🥖', 'Special Butter Pav Bhaji'),
    ('rest_10.svg', 'Havmor Ice Cream Parlour', 'Sundae Scoops, Kulfi & Shakes', '#0097A7', '#006064', '🍨', 'Gourmet Ice Creams'),
    ('rest_11.svg', 'Subway Highway Bites', 'Custom Fresh Subs, Salads & Wraps', '#2E7D32', '#1B5E20', '🥪', 'Fresh Subs & Salads'),
    ('rest_12.svg', 'Bakers Studio & Sweets', 'Artisan Cakes, Pastries & Dhokla', '#F06292', '#AD1457', '🎂', 'Fresh Bakery & Pastries'),
]

FOOD_THEMES = [
    ('food_1.svg', 'Gujarati Special Thali', 'Thali', '#FF5722', '#E64A19', '🍱', 'Unlimited Royal Thali'),
    ('food_2.svg', 'Paneer Butter Masala', 'North Indian', '#3F51B5', '#1A237E', '🍛', 'Rich Cashew Gravy'),
    ('food_3.svg', 'Cheese Burst Farmhouse Pizza', 'Pizza', '#D32F2F', '#B71C1C', '🍕', 'Fresh Mozzarella & Veggies'),
    ('food_4.svg', 'Mysore Masala Dosa', 'South Indian', '#388E3C', '#1B5E20', '🥞', 'Spicy Chutney & Crispy Crepe'),
    ('food_5.svg', 'Crunchy Double Veg Burger', 'Burger', '#FFA000', '#FF6F00', '🍔', 'Crispy Patty & Chipotle Mayo'),
    ('food_6.svg', 'Special Dum Biryani', 'Biryani', '#7B1FA2', '#4A148C', '🍲', 'Fragrant Basmati & Spices'),
    ('food_7.svg', 'Schezwan Hakka Noodles', 'Chinese', '#C2185B', '#880E4F', '🍜', 'Wok Tossed Fresh Veggies'),
    ('food_8.svg', 'Belgium Chocolate Waffle', 'Desserts', '#5D4037', '#3E2723', '🧇', 'Warm Dark Chocolate'),
    ('food_9.svg', 'Amul Butter Pav Bhaji', 'Fast Food', '#E65100', '#BF360C', '🥖', 'Tawa Spiced Bhaji with Buns'),
    ('food_10.svg', 'Kesar Pista Royal Sundae', 'Ice Cream', '#0097A7', '#006064', '🍨', 'Dry Fruit Infused Kulfi'),
    ('food_11.svg', 'Grilled Veggie Club Sub', 'Sandwich', '#2E7D32', '#1B5E20', '🥪', 'Toasted Multi-grain Bread'),
    ('food_12.svg', 'Dutch Truffle Pastry', 'Bakery', '#F06292', '#AD1457', '🍰', 'Layers of Pure Chocolate'),
]

def create_svg(filename, title, subtitle, c1, c2, emoji, badge, filepath):
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="100%" height="100%">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c1};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{c2};stop-opacity:1" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
  </defs>
  <!-- Background with Gradient -->
  <rect width="800" height="500" fill="url(#grad)" />
  
  <!-- Subtle Geometric Pattern Elements -->
  <circle cx="100" cy="80" r="140" fill="#ffffff" opacity="0.08" />
  <circle cx="720" cy="420" r="180" fill="#ffffff" opacity="0.06" />
  <rect x="600" y="-40" width="220" height="220" rx="40" transform="rotate(25 710 70)" fill="#ffffff" opacity="0.05" />
  
  <!-- Central Card Display -->
  <g filter="url(#shadow)">
    <!-- Food / Restaurant Emblem Icon -->
    <circle cx="400" cy="190" r="105" fill="#ffffff" />
    <text x="400" y="235" font-family="'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif" font-size="105" text-anchor="middle">{emoji}</text>
  </g>
  
  <!-- Badge Pill -->
  <rect x="250" y="325" width="300" height="38" rx="19" fill="#ffffff" opacity="0.22" />
  <text x="400" y="350" font-family="system-ui, -apple-system, sans-serif" font-size="16" font-weight="700" fill="#ffffff" text-anchor="middle" letter-spacing="1">{badge.upper()}</text>
  
  <!-- Main Title -->
  <text x="400" y="405" font-family="system-ui, -apple-system, sans-serif" font-size="34" font-weight="800" fill="#ffffff" text-anchor="middle" filter="url(#shadow)">{title}</text>
  
  <!-- Subtitle -->
  <text x="400" y="445" font-family="system-ui, -apple-system, sans-serif" font-size="19" font-weight="500" fill="#ffffff" opacity="0.9" text-anchor="middle">{subtitle}</text>
</svg>"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg_content)

def main():
    for fname, title, sub, c1, c2, emoji, badge in RESTAURANT_THEMES:
        path = os.path.join(RESTAURANTS_DIR, fname)
        create_svg(fname, title, sub, c1, c2, emoji, badge, path)
        print(f"Generated {path}")

    for fname, title, sub, c1, c2, emoji, badge in FOOD_THEMES:
        path = os.path.join(FOODS_DIR, fname)
        create_svg(fname, title, sub, c1, c2, emoji, badge, path)
        print(f"Generated {path}")

if __name__ == '__main__':
    main()
