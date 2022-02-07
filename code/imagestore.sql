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
  `id` INT NOT NULL AUTO_INCREMENT,
  `capacity` INT NOT NULL,
  `policy` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table `imagedb`.`statistics`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `imagedb`.`statistics` ;

CREATE TABLE IF NOT EXISTS `imagedb`.`statistics` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `items_num` INT NOT NULL,
  `item_size` INT NOT NULL,
  `request_num` INT NOT NULL,
  `miss_rate` FLOAT NOT NULL,
  `hit_rate` FLOAT NOT NULL,
  `count` INT NOT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;
-- -----------------------------------------------------
-- Data for table `imagedb`.`config`
-- -----------------------------------------------------
START TRANSACTION;
USE `imagedb`;
INSERT INTO `imagedb`.`config` (`id`, `capacity`, `policy`) VALUES (1, 20, 'Random Replacement');

-- -----------------------------------------------------
-- Data for table `imagedb`.`statistics`
-- -----------------------------------------------------
START TRANSACTION;
USE `imagedb`;
INSERT INTO `imagedb`.`statistics` (`id`, `items_num`, `item_size`, `request_num`, `miss_rate`, `hit_rate`, `count` ) VALUES (1, 20, 2, 20, 19.8, 28.9, 20);

COMMIT;



GRANT ALL PRIVILEGES ON imagedb.* TO 'ece1779'@'localhost';