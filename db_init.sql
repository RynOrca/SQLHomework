DROP DATABASE IF EXISTS GameKeyHub;
CREATE DATABASE GameKeyHub DEFAULT CHARACTER SET utf8mb4;
USE GameKeyHub;

CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    balance DECIMAL(10, 2) DEFAULT 0.00 COMMENT '钱包余额'
);

CREATE TABLE Games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    platform VARCHAR(20) DEFAULT 'Steam',
    historical_low DECIMAL(10, 2) DEFAULT 9999.99 COMMENT '史低价(自动维护)'
);

CREATE TABLE Product_Keys (
    key_id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    seller_id INT NOT NULL,
    cdk_code VARCHAR(100) NOT NULL COMMENT '激活码',
    price DECIMAL(10, 2) NOT NULL,
    status ENUM('available', 'sold') DEFAULT 'available',
    buyer_id INT DEFAULT NULL,
    FOREIGN KEY (game_id) REFERENCES Games(game_id),
    FOREIGN KEY (seller_id) REFERENCES Users(user_id)
);

CREATE TABLE Orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    buyer_id INT NOT NULL,
    key_id INT NOT NULL,
    deal_price DECIMAL(10, 2) NOT NULL,
    deal_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES Users(user_id),
    FOREIGN KEY (key_id) REFERENCES Product_Keys(key_id)
);


CREATE INDEX idx_game_stock ON Product_Keys(game_id, status);

DELIMITER //
CREATE TRIGGER trg_auto_update_low
AFTER INSERT ON Product_Keys
FOR EACH ROW
BEGIN
    DECLARE current_low DECIMAL(10, 2);
    SELECT historical_low INTO current_low FROM Games WHERE game_id = NEW.game_id;
    
    IF NEW.price < current_low THEN
        UPDATE Games SET historical_low = NEW.price WHERE game_id = NEW.game_id;
    END IF;
END //
DELIMITER ;

INSERT INTO Users (username, balance) VALUES ('Orca', 5000.00), ('MDY', 0.00),('Guan',9999.00);
INSERT INTO Games (title, platform) VALUES ('Black Myth: Wukong', 'Steam'), ('Elden Ring', 'Steam'), ('GTA VI', 'Rockstar');

INSERT INTO Product_Keys (game_id, seller_id, cdk_code, price) VALUES 
(1, 2, 'WM-8888-AAAA', 298.00),
(1, 2, 'WM-8888-BBBB', 268.00), 
(2, 2, 'ER-KEY-001', 199.00),
(3, 2, 'GTA-PRE-001', 399.00);


ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '0d000721';
FLUSH PRIVILEGES;