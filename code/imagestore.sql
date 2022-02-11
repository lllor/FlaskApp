-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

-- -----------------------------------------------------
-- Schema imagedb
-- -----------------------------------------------------
DROP SCHEMA IF EXISTS `imagedb`;

-- -----------------------------------------------------
-- Schema estore
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `imagedb` DEFAULT CHARACTER SET utf8 ;
USE `imagedb` ;

-- -----------------------------------------------------
-- Table `imagedb`.`image`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `imagedb`.`image` ;

CREATE TABLE IF NOT EXISTS `imagedb`.`image` (
  `key` VARCHAR(45) NOT NULL,
  `path` LONGTEXT NOT NULL,
  PRIMARY KEY (`key`))
ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `imagedb`.`config`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `imagedb`.`config` ;

CREATE TABLE IF NOT EXISTS `imagedb`.`config` (
  `policy` INT NOT NULL,
  `capacity` INT NOT NULL,
  PRIMARY KEY (`capacity`))
ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `imagedb`.`statistics`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `imagedb`.`statistics` ;

CREATE TABLE IF NOT EXISTS `imagedb`.`statistics` (
  `request_num` INT NOT NULL,
  `item_size` INT NOT NULL,
  `item_num` INT NOT NULL,
  `miss_num` INT NOT NULL,
  `hit_num` INT NOT NULL,
  `miss_rate` FLOAT NOT NULL,
  `hit_rate` FLOAT NOT NULL,
  PRIMARY KEY (`item_num`))
ENGINE = InnoDB;
-- -----------------------------------------------------
-- Data for table `imagedb`.`config`
-- -----------------------------------------------------
START TRANSACTION;
USE `imagedb`;
INSERT INTO `imagedb`.`config` (`policy`,`capacity`) VALUES (1,300);

-- -----------------------------------------------------
-- Data for table `imagedb`.`statistics`
-- -----------------------------------------------------
START TRANSACTION;
USE `imagedb`;
INSERT INTO `imagedb`.`statistics` (`request_num`, `item_size`, `item_num`, `miss_num`, `hit_num`, `miss_rate`, `hit_rate` ) VALUES (1, 20, 2, 20, 19, 28.9, 20.9);

COMMIT;



GRANT ALL PRIVILEGES ON imagedb.* TO 'ece1779'@'localhost';