/*
 * This file is part of Betaflight.
 *
 * Betaflight is free software. You can redistribute this software
 * and/or modify this software under the terms of the GNU General
 * Public License as published by the Free Software Foundation,
 * either version 3 of the License, or (at your option) any later
 * version.
 *
 * Betaflight is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this software.
 *
 * If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

#define FC_TARGET_MCU                   STM32F405

#define BOARD_NAME                      ORQA_F405
#define MANUFACTURER_ID                 ORQA
#define SYSTEM_HSE_MHZ                  8

/*
 * Factory boards use an MPU6000 aligned CW180. Later boards may carry an
 * ICM42688P in the same SPI1 position but with a different physical rotation.
 * Select that population with EXTRA_FLAGS=-DORQA_F405_IMU_ICM42688P.
 */
#define USE_ACC
#define USE_GYRO

#if defined(ORQA_F405_IMU_ICM42688P)
#define USE_ACC_SPI_ICM42688P
#define USE_GYRO_SPI_ICM42688P
#define GYRO_1_ALIGN                    CW0_DEG_FLIP
#else
#define USE_ACC_SPI_MPU6000
#define USE_GYRO_SPI_MPU6000
#define GYRO_1_ALIGN                    CW180_DEG
#endif

#define GYRO_1_SPI_INSTANCE             SPI1
#define GYRO_1_CS_PIN                   PA4
#define GYRO_1_EXTI_PIN                 PC4
#define ENSURE_MPU_DATA_READY_IS_LOW

/* DPS310 barometer and external QMC5883 compass on I2C1. */
#define USE_BARO
#define USE_BARO_DPS310
#define BARO_I2C_INSTANCE               I2CDEV_1
#define DEFAULT_BARO_I2C_ADDRESS        119

#define USE_MAG
#define USE_MAG_QMC5883
#define MAG_I2C_INSTANCE                I2CDEV_1
#define DASHBOARD_I2C_INSTANCE          I2CDEV_1

/* W25Q128FV blackbox flash on SPI3. */
#define USE_FLASH
#define USE_FLASH_W25Q128FV
#define FLASH_SPI_INSTANCE              SPI3
#define FLASH_CS_PIN                    PB3
#define DEFAULT_BLACKBOX_DEVICE         BLACKBOX_DEVICE_FLASH

/* Analog OSD on SPI2. */
#define USE_MAX7456
#define MAX7456_SPI_INSTANCE            SPI2
#define MAX7456_SPI_CS_PIN              PB12

/* Four motor outputs, two servo outputs, PPM input, and PWM beeper. */
#define MOTOR1_PIN                      PA3
#define MOTOR2_PIN                      PB0
#define MOTOR3_PIN                      PB1
#define MOTOR4_PIN                      PA2

#define SERVO1_PIN                      PA0
#define SERVO2_PIN                      PA1
#define RX_PPM_PIN                      PC9

#define BEEPER_PIN                      PA8
#define BEEPER_INVERTED
#define BEEPER_PWM_HZ                   4000

#define LED0_PIN                        PA15
#define LED1_PIN                        PB4

/* UART1: Ghost RC; UART3: GPS; UART5: ESC telemetry; UART6: telemetry. */
#define UART1_TX_PIN                    PA9
#define UART1_RX_PIN                    PA10
#define UART3_TX_PIN                    PB10
#define UART3_RX_PIN                    PB11
#define UART5_RX_PIN                    PD2
#define UART6_TX_PIN                    PC6
#define UART6_RX_PIN                    PC7

#define I2C1_SCL_PIN                    PB6
#define I2C1_SDA_PIN                    PB7

#define SPI1_SCK_PIN                    PA5
#define SPI1_SDI_PIN                    PA6
#define SPI1_SDO_PIN                    PA7
#define SPI2_SCK_PIN                    PB13
#define SPI2_SDI_PIN                    PB14
#define SPI2_SDO_PIN                    PB15
#define SPI3_SCK_PIN                    PC10
#define SPI3_SDI_PIN                    PC11
#define SPI3_SDO_PIN                    PB5

#define ADC_VBAT_PIN                    PC1
#define ADC_CURR_PIN                    PC3

#define PINIO1_PIN                      PB9
#define PINIO1_CONFIG                   1
#define PINIO1_BOX                      43
#define BOX_USER4_NAME                  "CAM SWITCH"

#define USB_DETECT_PIN                  PC5

/* Defaults recovered from the factory Betaflight 4.4.1 configuration. */
#define DEFAULT_RX_FEATURE              FEATURE_RX_SERIAL
#define SERIALRX_UART                   SERIAL_PORT_USART1
#define SERIALRX_PROVIDER               SERIALRX_GHST
#define GPS_UART                        SERIAL_PORT_USART3
#define ESC_SENSOR_UART                 SERIAL_PORT_UART5
#define DEFAULT_FEATURES                (FEATURE_TELEMETRY | FEATURE_OSD | FEATURE_GPS)
#define DEFAULT_MOTOR_DSHOT_SPEED       PWM_TYPE_DSHOT300
#define DEFAULT_DSHOT_TELEMETRY         DSHOT_TELEMETRY_ON

#define DEFAULT_VOLTAGE_METER_SOURCE    VOLTAGE_METER_ADC
#define DEFAULT_CURRENT_METER_SOURCE    CURRENT_METER_ADC
#define DEFAULT_VOLTAGE_METER_SCALE     112
#define DEFAULT_CURRENT_METER_SCALE     104

/* TIMER_PIN_MAP(index, pin, timer occurrence, DMA option). */
#define TIMER_PIN_MAPPING \
    TIMER_PIN_MAP( 0, MOTOR1_PIN, 1,  1) /* PA3 / TIM2_CH4 */ \
    TIMER_PIN_MAP( 1, MOTOR2_PIN, 2,  0) /* PB0 / TIM3_CH3 */ \
    TIMER_PIN_MAP( 2, MOTOR3_PIN, 2,  0) /* PB1 / TIM3_CH4 */ \
    TIMER_PIN_MAP( 3, MOTOR4_PIN, 1,  0) /* PA2 / TIM2_CH3 */ \
    TIMER_PIN_MAP( 4, SERVO1_PIN, 2,  0) /* PA0 / TIM5_CH1 */ \
    TIMER_PIN_MAP( 5, SERVO2_PIN, 2,  0) /* PA1 / TIM5_CH2 */ \
    TIMER_PIN_MAP( 6, RX_PPM_PIN, 2, -1) /* PC9 / TIM8_CH4 */ \
    TIMER_PIN_MAP( 7, BEEPER_PIN, 1, -1) /* PA8 / TIM1_CH1 */

#define ADC1_DMA_OPT                    1
