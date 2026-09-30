-- Skema Billard Hub (MySQL / TiDB)
-- Jalankan: mysql -u root -p < schema.sql
CREATE DATABASE IF NOT EXISTS billard_hub DEFAULT CHARACTER SET utf8mb4;
USE billard_hub;

CREATE TABLE IF NOT EXISTS user (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    username            VARCHAR(80)  NOT NULL UNIQUE,
    email               VARCHAR(120) NOT NULL UNIQUE,
    password            VARCHAR(255) NOT NULL,
    membership_tier     VARCHAR(20)  NOT NULL DEFAULT 'Biasa',
    membership_expiry   DATETIME     NULL,
    kaia_coin           INT          NOT NULL DEFAULT 50,
    active_booking_id   VARCHAR(50)  NULL,
    booking_expiry      DATETIME     NULL,
    booking_start_time  DATETIME     NULL,
    username_last_changed   DATETIME NULL,
    password_last_changed   DATETIME NULL,
    total_rupiah_spent  DECIMAL(12,2) NOT NULL DEFAULT 0.00
);

CREATE TABLE IF NOT EXISTS topup_log (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    kaia_amount   INT NOT NULL,
    rupiah_amount DECIMAL(12,2) NOT NULL,
    `timestamp`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_topup_user_time (user_id, `timestamp`)
);
