-- ========================================================
-- FOODIE HUNTER: Complete Relational MySQL Database Schema
-- Final Semester Major Project - Academic Standard
-- Target Engine: InnoDB | Charset: utf8mb4 | Collation: utf8mb4_unicode_ci
-- ========================================================

CREATE DATABASE IF NOT EXISTS `foody_hunters` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `foody_hunters`;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `admin_logs`;
DROP TABLE IF EXISTS `complaints`;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `favorites`;
DROP TABLE IF EXISTS `delivery_locations`;
DROP TABLE IF EXISTS `delivery_assignments`;
DROP TABLE IF EXISTS `delivery_partners`;
DROP TABLE IF EXISTS `reviews`;
DROP TABLE IF EXISTS `payments`;
DROP TABLE IF EXISTS `order_items`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `coupons`;
DROP TABLE IF EXISTS `cart_items`;
DROP TABLE IF EXISTS `cart`;
DROP TABLE IF EXISTS `food_items`;
DROP TABLE IF EXISTS `restaurant_categories`;
DROP TABLE IF EXISTS `food_categories`;
DROP TABLE IF EXISTS `restaurants`;
DROP TABLE IF EXISTS `addresses`;
DROP TABLE IF EXISTS `users`;

SET FOREIGN_KEY_CHECKS = 1;

-- --------------------------------------------------------
-- 1. Table: users
-- Stores authentication credentials, contact info, and profile details for all 4 roles
-- --------------------------------------------------------
CREATE TABLE `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(120) NOT NULL UNIQUE,
  `phone` VARCHAR(20) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('customer', 'restaurant', 'delivery', 'admin') NOT NULL DEFAULT 'customer',
  `gender` ENUM('male', 'female', 'other') DEFAULT NULL,
  `dob` DATE DEFAULT NULL,
  `address` TEXT DEFAULT NULL,
  `city` VARCHAR(60) DEFAULT 'Mehsana',
  `state` VARCHAR(60) DEFAULT 'Gujarat',
  `pincode` VARCHAR(10) DEFAULT '384001',
  `profile_pic` VARCHAR(255) DEFAULT NULL,
  `status` ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_users_role` (`role`),
  INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 2. Table: addresses
-- Customer saved delivery addresses with coordinates for route calculation
-- --------------------------------------------------------
CREATE TABLE `addresses` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `label` VARCHAR(50) DEFAULT 'Home',
  `address` TEXT NOT NULL,
  `area` VARCHAR(100) DEFAULT 'Radhanpur Road',
  `city` VARCHAR(60) DEFAULT 'Mehsana',
  `state` VARCHAR(60) DEFAULT 'Gujarat',
  `pincode` VARCHAR(10) DEFAULT '384002',
  `latitude` DECIMAL(10,7) DEFAULT 23.5880000,
  `longitude` DECIMAL(10,7) DEFAULT 72.3693000,
  `is_default` TINYINT(1) DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  INDEX `idx_addr_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 3. Table: restaurants
-- Food outlets located primarily in Mehsana, Gujarat with GPS coordinates
-- --------------------------------------------------------
CREATE TABLE `restaurants` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `owner_id` INT DEFAULT NULL,
  `name` VARCHAR(150) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `cuisine` VARCHAR(150) NOT NULL,
  `address` TEXT NOT NULL,
  `area` VARCHAR(100) DEFAULT 'Mehsana City',
  `city` VARCHAR(60) DEFAULT 'Mehsana',
  `state` VARCHAR(60) DEFAULT 'Gujarat',
  `pincode` VARCHAR(10) DEFAULT '384002',
  `phone` VARCHAR(20) DEFAULT NULL,
  `email` VARCHAR(120) DEFAULT NULL,
  `rating` DECIMAL(3,2) DEFAULT 4.50,
  `total_ratings` INT DEFAULT 0,
  `delivery_time` VARCHAR(30) DEFAULT '25-35 min',
  `delivery_fee` DECIMAL(8,2) DEFAULT 40.00,
  `min_order` DECIMAL(8,2) DEFAULT 100.00,
  `open_time` VARCHAR(10) DEFAULT '09:00',
  `close_time` VARCHAR(10) DEFAULT '23:00',
  `image` VARCHAR(255) DEFAULT NULL,
  `latitude` DECIMAL(10,7) DEFAULT 23.5880000,
  `longitude` DECIMAL(10,7) DEFAULT 72.3693000,
  `verification_status` ENUM('pending', 'approved', 'rejected', 'suspended') DEFAULT 'approved',
  `status` ENUM('active', 'inactive') DEFAULT 'active',
  `is_open` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`owner_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
  INDEX `idx_rest_area` (`area`),
  INDEX `idx_rest_rating` (`rating`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 4. Table: food_categories
-- Cuisine and item categorizations across the catalog
-- --------------------------------------------------------
CREATE TABLE `food_categories` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(60) NOT NULL UNIQUE,
  `icon` VARCHAR(50) DEFAULT '🍽️',
  `image` VARCHAR(255) DEFAULT NULL,
  `description` TEXT DEFAULT NULL,
  `is_active` TINYINT(1) DEFAULT 1,
  `sort_order` INT DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 5. Table: restaurant_categories
-- Many-to-many relationship between restaurants and categories
-- --------------------------------------------------------
CREATE TABLE `restaurant_categories` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `restaurant_id` INT NOT NULL,
  `category_id` INT NOT NULL,
  FOREIGN KEY (`restaurant_id`) REFERENCES `restaurants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`category_id`) REFERENCES `food_categories`(`id`) ON DELETE CASCADE,
  UNIQUE KEY `uniq_rest_cat` (`restaurant_id`, `category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 6. Table: food_items
-- Comprehensive food dish catalog attached to restaurants
-- --------------------------------------------------------
CREATE TABLE `food_items` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `restaurant_id` INT NOT NULL,
  `category_id` INT NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `price` DECIMAL(8,2) NOT NULL,
  `discount` DECIMAL(8,2) DEFAULT 0.00,
  `final_price` DECIMAL(8,2) NOT NULL,
  `image` VARCHAR(255) DEFAULT NULL,
  `veg_type` ENUM('veg', 'non_veg') DEFAULT 'veg',
  `preparation_time` INT DEFAULT 20,
  `availability` TINYINT(1) DEFAULT 1,
  `is_bestseller` TINYINT(1) DEFAULT 0,
  `rating` DECIMAL(3,2) DEFAULT 4.50,
  `total_ratings` INT DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`restaurant_id`) REFERENCES `restaurants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`category_id`) REFERENCES `food_categories`(`id`) ON DELETE CASCADE,
  INDEX `idx_food_rest` (`restaurant_id`),
  INDEX `idx_food_cat` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 7. Table: cart
-- Active customer shopping cart container
-- --------------------------------------------------------
CREATE TABLE `cart` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `status` ENUM('active', 'completed', 'abandoned') DEFAULT 'active',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  INDEX `idx_cart_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 8. Table: cart_items
-- Food dishes inside the active shopping cart
-- --------------------------------------------------------
CREATE TABLE `cart_items` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `cart_id` INT NOT NULL,
  `food_item_id` INT NOT NULL,
  `quantity` INT NOT NULL DEFAULT 1,
  `price` DECIMAL(8,2) NOT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`cart_id`) REFERENCES `cart`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`food_item_id`) REFERENCES `food_items`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 9. Table: coupons
-- Discount vouchers with rules and limits
-- --------------------------------------------------------
CREATE TABLE `coupons` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `code` VARCHAR(50) NOT NULL UNIQUE,
  `description` VARCHAR(255) DEFAULT NULL,
  `discount_type` ENUM('percentage', 'fixed') DEFAULT 'percentage',
  `discount_value` DECIMAL(8,2) NOT NULL,
  `max_discount` DECIMAL(8,2) DEFAULT NULL,
  `min_order_amount` DECIMAL(8,2) DEFAULT 0.00,
  `expiry_date` DATE DEFAULT NULL,
  `usage_limit` INT DEFAULT 1000,
  `times_used` INT DEFAULT 0,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 10. Table: orders
-- Master customer order transactions with full lifecycle
-- --------------------------------------------------------
CREATE TABLE `orders` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `order_code` VARCHAR(50) NOT NULL UNIQUE,
  `user_id` INT NOT NULL,
  `restaurant_id` INT NOT NULL,
  `address_id` INT DEFAULT NULL,
  `delivery_address` TEXT NOT NULL,
  `customer_lat` DECIMAL(10,7) DEFAULT 23.5880000,
  `customer_lng` DECIMAL(10,7) DEFAULT 72.3693000,
  `total_amount` DECIMAL(10,2) NOT NULL,
  `delivery_fee` DECIMAL(8,2) DEFAULT 40.00,
  `discount` DECIMAL(8,2) DEFAULT 0.00,
  `tax` DECIMAL(8,2) DEFAULT 0.00,
  `payment_method` VARCHAR(50) DEFAULT 'cod',
  `payment_status` ENUM('pending', 'paid', 'failed', 'refunded') DEFAULT 'pending',
  `order_status` ENUM(
    'placed',
    'confirmed',
    'preparing',
    'ready_for_pickup',
    'assigned',
    'picked_up',
    'out_for_delivery',
    'delivered',
    'cancelled',
    'rejected'
  ) DEFAULT 'placed',
  `coupon_id` INT DEFAULT NULL,
  `notes` TEXT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`restaurant_id`) REFERENCES `restaurants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`address_id`) REFERENCES `addresses`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`coupon_id`) REFERENCES `coupons`(`id`) ON DELETE SET NULL,
  INDEX `idx_order_user` (`user_id`),
  INDEX `idx_order_rest` (`restaurant_id`),
  INDEX `idx_order_status` (`order_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 11. Table: order_items
-- Itemized snapshot of food items ordered in an order
-- --------------------------------------------------------
CREATE TABLE `order_items` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `order_id` INT NOT NULL,
  `food_item_id` INT NOT NULL,
  `item_name` VARCHAR(150) NOT NULL,
  `quantity` INT NOT NULL DEFAULT 1,
  `price` DECIMAL(8,2) NOT NULL,
  `subtotal` DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`food_item_id`) REFERENCES `food_items`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 12. Table: payments
-- Payment transaction records (Academic Demo Payment Gateway)
-- --------------------------------------------------------
CREATE TABLE `payments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `order_id` INT NOT NULL,
  `transaction_id` VARCHAR(100) NOT NULL UNIQUE,
  `payment_method` VARCHAR(50) NOT NULL,
  `amount` DECIMAL(10,2) NOT NULL,
  `payment_status` ENUM('pending', 'paid', 'failed', 'refunded') DEFAULT 'paid',
  `payment_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 13. Table: delivery_partners
-- Courier partner profiles, vehicles, and live coordinate cache
-- --------------------------------------------------------
CREATE TABLE `delivery_partners` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL UNIQUE,
  `vehicle_type` VARCHAR(50) DEFAULT 'Motorcycle',
  `vehicle_number` VARCHAR(50) DEFAULT 'GJ-02-AB-1234',
  `license_number` VARCHAR(50) DEFAULT 'DL-GJ02-2022-00123',
  `is_available` TINYINT(1) DEFAULT 1,
  `is_online` TINYINT(1) DEFAULT 1,
  `current_lat` DECIMAL(10,7) DEFAULT 23.5880000,
  `current_lng` DECIMAL(10,7) DEFAULT 72.3693000,
  `total_deliveries` INT DEFAULT 0,
  `total_earnings` DECIMAL(10,2) DEFAULT 0.00,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 14. Table: delivery_assignments
-- Link dispatch between orders and delivery partners
-- --------------------------------------------------------
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

-- --------------------------------------------------------
-- 15. Table: delivery_locations
-- Historical breadcrumbs & live GPS coordinates logged during active deliveries
-- --------------------------------------------------------
CREATE TABLE `delivery_locations` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `delivery_partner_id` INT NOT NULL,
  `order_id` INT NOT NULL,
  `latitude` DECIMAL(10,7) NOT NULL,
  `longitude` DECIMAL(10,7) NOT NULL,
  `recorded_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`delivery_partner_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE,
  INDEX `idx_deliv_loc_order` (`order_id`, `recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 16. Table: reviews
-- Customer star ratings (1-5) and feedback for completed orders
-- --------------------------------------------------------
CREATE TABLE `reviews` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `restaurant_id` INT NOT NULL,
  `order_id` INT DEFAULT NULL,
  `rating` INT NOT NULL,
  `comment` TEXT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`restaurant_id`) REFERENCES `restaurants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 17. Table: favorites
-- Customer bookmarked / wishlisted restaurants and food dishes
-- --------------------------------------------------------
CREATE TABLE `favorites` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `item_type` ENUM('restaurant', 'food') NOT NULL,
  `item_id` INT NOT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  UNIQUE KEY `uniq_fav` (`user_id`, `item_type`, `item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 18. Table: notifications
-- In-app notifications for order tracking, alerts, and management events
-- --------------------------------------------------------
CREATE TABLE `notifications` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `role` ENUM('customer', 'restaurant', 'delivery', 'admin') DEFAULT 'customer',
  `title` VARCHAR(150) NOT NULL,
  `message` TEXT NOT NULL,
  `link` VARCHAR(255) DEFAULT NULL,
  `is_read` TINYINT(1) DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  INDEX `idx_notif_user` (`user_id`, `is_read`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 19. Table: complaints
-- Customer grievance tickets and contact enquiries
-- --------------------------------------------------------
CREATE TABLE `complaints` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT DEFAULT NULL,
  `name` VARCHAR(100) DEFAULT NULL,
  `email` VARCHAR(100) DEFAULT NULL,
  `order_id` INT DEFAULT NULL,
  `subject` VARCHAR(150) DEFAULT NULL,
  `message` TEXT DEFAULT NULL,
  `status` ENUM('open', 'in_progress', 'resolved') DEFAULT 'open',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 20. Table: admin_logs
-- Audit trail of major administrative actions
-- --------------------------------------------------------
CREATE TABLE `admin_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `admin_id` INT DEFAULT NULL,
  `action` VARCHAR(100) NOT NULL,
  `details` TEXT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`admin_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
