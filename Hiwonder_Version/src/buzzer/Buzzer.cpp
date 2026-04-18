#include "./../../Hiwonder.hpp"
#include <Arduino.h>

#define BUZZER_TASK_PERIOD  ((float)30) /* Buzzer status refresh interval (ms) (蜂鸣器状态刷新间隔(ms)) */

static void buzzer_control_callback(Buzzer_t* obj)
{
  /* Try to fetch new control data from the queue; if successful, reset the state machine and start a new control loop (尝试从队列中取的新的控制数据，如果成功取出则重置状态机重新开始一个控制循环) */
    if(obj->new_flag != 0) {
        obj->new_flag = 0;
        obj->stage = BUZZER_STAGE_START_NEW_CYCLE;
    }
    /* State machine processing (状态机处理) */
    switch(obj->stage) {
        case BUZZER_STAGE_START_NEW_CYCLE: {
            if(obj->ticks_on > 0 && obj->freq > 0) {
                ledcWriteTone(obj->buzzer_channel , obj->freq); /* Activate the buzzer (鸣响蜂鸣器) */
                if(obj->ticks_off > 0) {/* If silence time is not zero, it means beeping; otherwise, it means continuous sound (静音时间不为 0 即为嘀嘀响，否则就是长鸣) */
                    obj->ticks_count = 0;
                    obj->stage = BUZZER_STAGE_WATTING_OFF; /* Wait until the sound duration ends (等到鸣响时间结束) */
                }else{
					obj->stage = BUZZER_STAGE_IDLE; /* Continuous sound, switch to idle state (长鸣，转入空闲) */
				}
            } else { /* As long as the sound duration is zero, it means silence (只要鸣响时间为 0 即为静音) */
                ledcWriteTone(obj->buzzer_channel , 0);
				obj->stage = BUZZER_STAGE_IDLE;  /* Long silence, switch to idle state (长静音，转入空闲) */
            }
            break;
        }
        case BUZZER_STAGE_WATTING_OFF: {
            obj->ticks_count += BUZZER_TASK_PERIOD;
            if(obj->ticks_count >= obj->ticks_on) { /* Sound duration ended (鸣响时间结束) */
                ledcWriteTone(obj->buzzer_channel , 0);
                obj->stage = BUZZER_STAGE_WATTING_PERIOD_END;
            }
            break;
        }
        case BUZZER_STAGE_WATTING_PERIOD_END: { /* Wait for the cycle to end (等待周期结束) */
            obj->ticks_count += BUZZER_TASK_PERIOD;
            if(obj->ticks_count >= (obj->ticks_off + obj->ticks_on)) {
                obj->ticks_count -= (obj->ticks_off + obj->ticks_on);
                if(obj->repeat == 1) { /* When the remaining repeat count is 1, the control task can end (剩余重复次数为1时就可以结束此次控制任务) */
                    ledcWriteTone(obj->buzzer_channel , 0);
                    obj->stage = BUZZER_STAGE_IDLE;
                } else {
                    ledcWriteTone(obj->buzzer_channel , obj->freq);
                    obj->repeat = obj->repeat == 0 ? 0 : obj->repeat - 1;
                    obj->stage = BUZZER_STAGE_WATTING_OFF;
                }
            }
            break;
        }
        case BUZZER_STAGE_IDLE: {
            break;
        }
        default:
            break;
    }
}


void Buzzer_t::init(uint8_t pin , uint8_t channel , uint16_t frequency)
{
    buzzer_pin = pin;
    stage = BUZZER_STAGE_IDLE;
    ticks_count = 0;
    freq = frequency;
    buzzer_channel = channel;
    //ledcSetup(buzzer_channel,frequency,12);
    //ledcAttachPin(buzzer_pin, buzzer_channel);
    ledcAttachChannel(buzzer_pin,frequency,12,buzzer_channel);
    ledcWrite(buzzer_channel, 2048);
    ledcWriteTone(buzzer_channel , 0);
    timer_buzzer.attach((BUZZER_TASK_PERIOD/1000), buzzer_control_callback , this);
}

void Buzzer_t::on_off(uint8_t state)
{
  if(state != 0)
  {
    blink(1500 , 200 , 400 , 0);
  }else{
    blink(1500 , 0 , 400 , 0);
  }
}

void Buzzer_t::blink(uint16_t frequency , uint16_t on_time , uint16_t off_time , uint16_t count)
{
    new_flag = 1;
    freq = frequency;
    ticks_on = on_time;
    ticks_off = off_time;
    repeat = count;
}
