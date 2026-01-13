DROP DATABASE IF EXISTS GameKeyHub;
CREATE DATABASE GameKeyHub DEFAULT CHARACTER SET utf8mb4;
USE GameKeyHub;

-- 1. 用户表
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user',
    balance DECIMAL(10, 2) DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. 游戏表
CREATE TABLE Games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    platform VARCHAR(20) DEFAULT 'Steam',
    historical_low DECIMAL(10, 2) DEFAULT 9999.99,
    is_active BOOLEAN DEFAULT TRUE COMMENT '1=上架, 0=下架'
);

-- 3. 商品表
CREATE TABLE Product_Keys (
    key_id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    seller_id INT NOT NULL,
    cdk_code VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    status ENUM('available', 'sold') DEFAULT 'available',
    buyer_id INT DEFAULT NULL,
    FOREIGN KEY (game_id) REFERENCES Games(game_id),
    FOREIGN KEY (seller_id) REFERENCES Users(user_id)
);

-- 4. 订单表
CREATE TABLE Orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    buyer_id INT NOT NULL,
    key_id INT NOT NULL,
    deal_price DECIMAL(10, 2) NOT NULL,
    deal_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES Users(user_id),
    FOREIGN KEY (key_id) REFERENCES Product_Keys(key_id)
);

-- 索引与触发器
CREATE INDEX idx_game_status ON Product_Keys(game_id, status);

DELIMITER //
CREATE TRIGGER trg_auto_update_low
AFTER INSERT ON Product_Keys
FOR EACH ROW
BEGIN
    DECLARE current_low DECIMAL(10, 2);
    SELECT historical_low INTO current_low FROM Games WHERE game_id = NEW.game_id;
    IF NEW.price < current_low OR current_low IS NULL THEN
        UPDATE Games SET historical_low = NEW.price WHERE game_id = NEW.game_id;
    END IF;
END //
DELIMITER ;

-- === 初始化数据 ===
-- 预设一个管理员账户: admin / 123456
-- 哈希值对应 '123456'
INSERT INTO Users (username, password_hash, role, balance) VALUES 
('admin', 'scrypt:32768:8:1$k1j2l3k4$5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'admin', 99999.00);

-- 初始化游戏
INSERT INTO Games (title, platform) VALUES 
('Black Myth: Wukong', 'Steam'), 
('Elden Ring', 'Steam'),
('GTA VI', 'Rockstar');

-- 将 password 改为你真正的密码
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '0d000721';
FLUSH PRIVILEGES;