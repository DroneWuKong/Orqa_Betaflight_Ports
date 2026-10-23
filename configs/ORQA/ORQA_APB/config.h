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

#define FC_TARGET_MCU                   STM32H743

#define BOARD_NAME                      ORQA_APB
#define MANUFACTURER_ID                 ORQA
#define SYSTEM_HSE_MHZ                  8

/*
 * APB IMU populations have different chips and, on SPI4, different physical
 * rotations. The default is ORQA's original MPU6000 + ICM42605 population.
 * Build a later ICM42688P population with:
 *
 *   EXTRA_FLAGS=-DORQA_APB_IMU_ICM42688P
 */
#define USE_ACC
#define USE_GYRO

#if defined(ORQA_APB_IMU_ICM42688P)
#define USE_ACC_SPI_ICM42688P
#define USE_GYRO_SPI_ICM42688P
#define GYRO_1_ALIGN                    CW0_DEG_FLIP
#define GYRO_2_ALIGN                    CW90_DEG_FLIP
#else
#define USE_ACC_SPI_MPU6000
#define USE_GYRO_SPI_MPU6000
#define USE_ACC_SPI_ICM42605
#define USE_GYRO_SPI_ICM42605
#define GYRO_1_ALIGN                    CW0_DEG_FLIP
#define GYRO_2_ALIGN                    CW0_DEG_FLIP
#endif

#define GYRO_1_SPI_INSTANCE             SPI1
#define GYRO_1_CS_PIN                   PA4
#define GYRO_1_EXTI_PIN                 PC3

#define GYRO_2_SPI_INSTANCE             SPI4
#define GYRO_2_CS_PIN                   PE11
#define GYRO_2_EXTI_PIN                 PE10

#define DEFAULT_GYRO_TO_USE             GYRO_CONFIG_USE_GYRO_BOTH
#define ENSURE_MPU_DATA_READY_IS_LOW

/* DPS310 at I2C address 0x77. */
#define USE_BARO
#define USE_BARO_DPS310
#define BARO_I2C_INSTANCE               I2CDEV_2
#define DEFAULT_BARO_I2C_ADDRESS        119

/* External compass/dashboard connector. */
#define USE_MAG
#define USE_MAG_QMC5883
#define MAG_I2C_INSTANCE                I2CDEV_1
#define DASHBOARD_I2C_INSTANCE          I2CDEV_1

/* W25Q128FV blackbox flash on SPI2. */
#define USE_FLASH
#define USE_FLASH_W25Q128FV
#define FLASH_SPI_INSTANCE              SPI2
#define FLASH_CS_PIN                    PB12
#define DEFAULT_BLACKBOX_DEVICE         BLACKBOX_DEVICE_FLASH

/* Analog OSD on SPI3. */
#define USE_MAX7456
#define MAX7456_SPI_INSTANCE            SPI3
#define MAX7456_SPI_CS_PIN              PA15

/* APB motor and servo connector order. */
#define MOTOR1_PIN                      PD13
#define MOTOR2_PIN                      PD12
#define MOTOR3_PIN                      PA1
#define MOTOR4_PIN                      PA0
#define MOTOR5_PIN                      PA2
#define MOTOR6_PIN                      PA3
#define MOTOR7_PIN                      PB1
#define MOTOR8_PIN                      PB0

#define SERVO1_PIN                      PE6
#define SERVO2_PIN                      PE5
/* PD14 shares TIM4 with motors 1/2; do not advertise an independent servo. */

#define BEEPER_PIN                      PE9
#define BEEPER_INVERTED
#define BEEPER_PWM_HZ                   4000

/* APB status LEDs are active low. */
#define LED0_PIN                        PA8
#define LED1_PIN                        PA10
#define LED2_PIN                        PD11
#define LED0_INVERTED
#define LED1_INVERTED
#define LED2_INVERTED

/*
 * UART3: Ghost RC
 * UART4: internal i.MX8M Plus companion bridge
 * UART6: external telemetry / SiK / gimbal
 * UART7: GPS
 * UART8: ESC telemetry
 */
#define UART3_TX_PIN                    PD8
#define UART3_RX_PIN                    PD9
#define UART4_TX_PIN                    PC10
#define UART4_RX_PIN                    PC11
#define UART6_TX_PIN                    PC6
#define UART6_RX_PIN                    PC7
#define UART7_TX_PIN                    PE8
#define UART7_RX_PIN                    PE7
/* ESC telemetry is RX-only; do not expose an unverified TX pad. */
#define UART8_RX_PIN                    PE0

/* I2C1 is external; I2C2 carries the onboard barometer. */
#define I2C1_SCL_PIN                    PB6
#define I2C1_SDA_PIN                    PB7
#define I2C2_SCL_PIN                    PB10
#define I2C2_SDA_PIN                    PB11

/* SPI buses. */
#define SPI1_SCK_PIN                    PA5
#define SPI1_SDI_PIN                    PA6
#define SPI1_SDO_PIN                    PA7
#define SPI2_SCK_PIN                    PB13
#define SPI2_SDI_PIN                    PB14
#define SPI2_SDO_PIN                    PB15
#define SPI3_SCK_PIN                    PB3
#define SPI3_SDI_PIN                    PB4
#define SPI3_SDO_PIN                    PD6
#define SPI4_SCK_PIN                    PE12
#define SPI4_SDI_PIN                    PE13
#define SPI4_SDO_PIN                    PE14

/* USB FS: PA11/PA12 data; APB VBUS sense is PE2. */
#define USB_DETECT_PIN                  PE2

/* Battery voltage/current sensing. */
#define ADC_VBAT_PIN                    PC0
#define ADC_CURR_PIN                    PC1
#define DEFAULT_VOLTAGE_METER_SOURCE    VOLTAGE_METER_ADC
#define DEFAULT_CURRENT_METER_SOURCE    CURRENT_METER_ADC
#define DEFAULT_VOLTAGE_METER_SCALE     112
#define DEFAULT_CURRENT_METER_SCALE     108

/* Camera switch on USER4. */
#define PINIO1_PIN                      PD0
#define PINIO1_CONFIG                   1
#define PINIO1_BOX                      43
#define BOX_USER4_NAME                  "CAM SWITCH"

/* Companion Blackbox offload: MSP UART4, upstream default 115200 baud. */
#define MSP_UART                        SERIAL_PORT_UART4
#define DEFAULT_RX_FEATURE              FEATURE_RX_SERIAL
#define SERIALRX_UART                   SERIAL_PORT_USART3
#define SERIALRX_PROVIDER               SERIALRX_GHST
#define GPS_UART                        SERIAL_PORT_USART7
#define ESC_SENSOR_UART                 SERIAL_PORT_USART8
#define DEFAULT_FEATURES                (FEATURE_TELEMETRY | FEATURE_OSD | FEATURE_GPS)
#define DEFAULT_MOTOR_DSHOT_SPEED       PWM_TYPE_DSHOT300
#define DEFAULT_DSHOT_TELEMETRY         DSHOT_TELEMETRY_ON

/* TIMER_PIN_MAP(index, pin, timer occurrence, DMA option). */
#define TIMER_PIN_MAPPING \
    TIMER_PIN_MAP( 0, MOTOR1_PIN, 1,  6) /* PD13 / TIM4_CH2  */ \
    TIMER_PIN_MAP( 1, MOTOR2_PIN, 1,  7) /* PD12 / TIM4_CH1  */ \
    TIMER_PIN_MAP( 2, MOTOR3_PIN, 2,  3) /* PA1  / TIM5_CH2  */ \
    TIMER_PIN_MAP( 3, MOTOR4_PIN, 2,  2) /* PA0  / TIM5_CH1  */ \
    TIMER_PIN_MAP( 4, MOTOR5_PIN, 2,  4) /* PA2  / TIM5_CH3  */ \
    TIMER_PIN_MAP( 5, MOTOR6_PIN, 2,  5) /* PA3  / TIM5_CH4  */ \
    TIMER_PIN_MAP( 6, MOTOR7_PIN, 2,  1) /* PB1  / TIM3_CH4  */ \
    TIMER_PIN_MAP( 7, MOTOR8_PIN, 2,  0) /* PB0  / TIM3_CH3  */ \
    TIMER_PIN_MAP( 8, SERVO1_PIN, 1, -1) /* PE6  / TIM15_CH2 */ \
    TIMER_PIN_MAP( 9, SERVO2_PIN, 1, -1) /* PE5  / TIM15_CH1 */ \
    TIMER_PIN_MAP(10, BEEPER_PIN, 1, -1) /* PE9  / TIM1_CH1  */

#define ADC1_DMA_OPT                    8
#define ADC3_DMA_OPT                    9
