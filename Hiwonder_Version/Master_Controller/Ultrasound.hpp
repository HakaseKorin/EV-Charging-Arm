#ifndef ULTRASOUND_H
#define ULTRASOUND_H

#include <Arduino.h>
#include "IIC.hpp"

#define ULTRASOUND_I2C_ADDR 0x77 

//Register (寄存器)
#define DISDENCE_L    0//Distance lower 8 bits, unit: mm (距离低8位，单位mm)
#define DISDENCE_H    1

#define RGB_BRIGHTNESS  50//0-255

#define RGB_WORK_MODE 2//RGB light mode, 0: user-defined mode, 1: breathing light mode, default 0 (RGB灯模式，0：用户自定义模式 1：呼吸灯模式 默认0)

#define RGB1_R      3//R value of probe 1, range 0~255, default 0 (1号探头的R值，0~255，默认0)
#define RGB1_G      4//Default 0 (默认0)
#define RGB1_B      5//Default 255 (默认255)

#define RGB2_R      6//R value of probe 2, range 0~255, default 0 (2号探头的R值，0~255，默认0)
#define RGB2_G      7//Default 0 (默认0)
#define RGB2_B      8//Default 255 (默认255)

#define RGB1_R_BREATHING_CYCLE      9 //Breathing cycle of R value for probe 1 in breathing mode, unit: 100ms, default 0 (呼吸灯模式时，1号探头的R的呼吸周期，单位100ms，默认0)
                                      //If set to 3000ms, this value is 30 (如果设置周期3000ms，则此值为30)
#define RGB1_G_BREATHING_CYCLE      10
#define RGB1_B_BREATHING_CYCLE      11

#define RGB2_R_BREATHING_CYCLE      12//Probe 2 (2号探头)
#define RGB2_G_BREATHING_CYCLE      13
#define RGB2_B_BREATHING_CYCLE      14

#define RGB_WORK_SIMPLE_MODE    0
#define RGB_WORK_BREATHING_MODE   1

class Ultrasound {
  private:
    IIC* iic;
  public:
    Ultrasound();
    void init(IIC* iic_obj);
    void Breathing(uint8_t r1, uint8_t g1, uint8_t b1, uint8_t r2, uint8_t g2, uint8_t b2);
    void Color(uint8_t r1, uint8_t g1, uint8_t b1, uint8_t r2, uint8_t g2, uint8_t b2);
    uint16_t GetDistance();
};
#endif
