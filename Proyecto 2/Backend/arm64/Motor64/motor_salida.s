.global decidir_accion
.global print_error
.global print_manual

.data
err_input:
    .ascii "STATUS=ERROR\nERROR=INVALID_INPUT\nDETAIL=EXPECTED_7_FIELDS\n"
len_err_input = . - err_input

val_alarm: .ascii "ALARM_ON\n"
len_val_alarm = . - val_alarm
val_riego1: .ascii "RIEGO_1_ON\n"
len_val_riego1 = . - val_riego1
val_riego2: .ascii "RIEGO_2_ON\n"
len_val_riego2 = . - val_riego2
val_light: .ascii "LIGHT_ON\n"
len_val_light = . - val_light
val_fan: .ascii "FAN_ON\n"
len_val_fan = . - val_fan
val_green: .ascii "LED_GREEN\n"
len_val_green = . - val_green
val_no_action: .ascii "NO_ACTION\n"
len_val_no_action = . - val_no_action

key_action: .ascii "ACTION="
len_key_action = . - key_action
key_target: .ascii "TARGET="
len_key_target = . - key_target
key_risk: .ascii "RISK="
len_key_risk = . - key_risk
key_reason: .ascii "REASON="
len_key_reason = . - key_reason
key_value: .ascii "VALUE="
len_key_value = . - key_value
key_indicator: .ascii "INDICATOR="
len_key_indicator = . - key_indicator
key_status: .ascii "STATUS=OK\n"
len_key_status = . - key_status

target_gas: .ascii "GAS\n"
len_target_gas = . - target_gas
target_soil1: .ascii "SOIL1\n"
len_target_soil1 = . - target_soil1
target_soil2: .ascii "SOIL2\n"
len_target_soil2 = . - target_soil2
target_luz: .ascii "LUZ\n"
len_target_luz = . - target_luz
target_temp: .ascii "TEMP\n"
len_target_temp = . - target_temp
target_general: .ascii "GENERAL\n"
len_target_general = . - target_general

risk_critical: .ascii "CRITICAL\n"
len_risk_critical = . - risk_critical
risk_high: .ascii "HIGH\n"
len_risk_high = . - risk_high
risk_low: .ascii "LOW\n"
len_risk_low = . - risk_low

reason_gas_high: .ascii "GAS_HIGH_OR_UNSTABLE\n"
len_reason_gas_high = . - reason_gas_high
reason_soil1_low: .ascii "SOIL1_LOW_AND_DESCENDING\n"
len_reason_soil1_low = . - reason_soil1_low
reason_soil2_low: .ascii "SOIL2_LOW_AND_DESCENDING\n"
len_reason_soil2_low = . - reason_soil2_low
reason_luz_low: .ascii "LUZ_LOW_AND_DESCENDING\n"
len_reason_luz_low = . - reason_luz_low
reason_temp_high: .ascii "TEMP_HIGH_AND_ASCENDING\n"
len_reason_temp_high = . - reason_temp_high
reason_normal: .ascii "NORMAL_CONDITIONS\n"
len_reason_normal = . - reason_normal
reason_manual: .ascii "MANUAL_MODE\n"
len_reason_manual = . - reason_manual
reason_startup: .ascii "NOT_ENOUGH_DATA\n"
len_reason_startup = . - reason_startup

newline:
    .ascii "\n"

num_buffer:
    .skip 32

.text

// Prioridades
// 1 GAS alto o amplitud GAS alta = ALARM_ON
// 2 SUELO1 bajo y tendencia descendente = RIEGO_1_ON
// 3 SUELO2 bajo y tendencia descendente = RIEGO_2_ON
// 4 LUZ baja y tendencia descendente = LIGHT_ON
// 5 TEMP alta y tendencia ascendente = FAN_ON
// 6 LED_GREEN
decidir_accion:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    ldr x0, =hist_count
    ldr x1, [x0]
    cmp x1, #5
    blt print_startup

    // GAS promedio alto o amplitud alta 
    cmp x9, #80
    bge print_alarm

    cmp x10, #150
    bge print_alarm

    // SUELO1 promedio bajo 
    cmp x11, #35
    blt print_riego1

check_suelo2:
    // SUELO2 promedio bajo
    cmp x13, #35
    blt print_riego2

check_luz:
    // LUZ promedio alta (oscuridad) >= 850
    cmp x15, #850
    bge print_light

check_temp:
    // TEMP promedio alta
    cmp x17, #30
    bge print_fan

    b print_green

// Macros for generic structured printing
print_alarm:
    ldr x1, =val_alarm
    mov x2, #len_val_alarm
    ldr x3, =target_gas
    mov x4, #len_target_gas
    ldr x5, =risk_critical
    mov x6, #len_risk_critical
    ldr x7, =reason_gas_high
    mov x8, #len_reason_gas_high
    mov x19, x9 // Value = avg gas
    mov x20, x10 // Indicator = amp gas
    bl print_structured
    ldp x29, x30, [sp], #16
    ret

print_riego1:
    ldr x1, =val_riego1
    mov x2, #len_val_riego1
    ldr x3, =target_soil1
    mov x4, #len_target_soil1
    ldr x5, =risk_high
    mov x6, #len_risk_high
    ldr x7, =reason_soil1_low
    mov x8, #len_reason_soil1_low
    mov x19, x11 // avg suelo1
    mov x20, x12 // trend suelo1
    bl print_structured
    ldp x29, x30, [sp], #16
    ret

print_riego2:
    ldr x1, =val_riego2
    mov x2, #len_val_riego2
    ldr x3, =target_soil2
    mov x4, #len_target_soil2
    ldr x5, =risk_high
    mov x6, #len_risk_high
    ldr x7, =reason_soil2_low
    mov x8, #len_reason_soil2_low
    mov x19, x13 // avg suelo2
    mov x20, x14 // trend suelo2
    bl print_structured
    ldp x29, x30, [sp], #16
    ret

print_light:
    ldr x1, =val_light
    mov x2, #len_val_light
    ldr x3, =target_luz
    mov x4, #len_target_luz
    ldr x5, =risk_low
    mov x6, #len_risk_low
    ldr x7, =reason_luz_low
    mov x8, #len_reason_luz_low
    mov x19, x15 // avg luz
    mov x20, x16 // trend luz
    bl print_structured
    ldp x29, x30, [sp], #16
    ret

print_fan:
    ldr x1, =val_fan
    mov x2, #len_val_fan
    ldr x3, =target_temp
    mov x4, #len_target_temp
    ldr x5, =risk_low
    mov x6, #len_risk_low
    ldr x7, =reason_temp_high
    mov x8, #len_reason_temp_high
    mov x19, x17 // avg temp
    mov x20, x18 // trend temp
    bl print_structured
    ldp x29, x30, [sp], #16
    ret

print_green:
    ldr x1, =val_green
    mov x2, #len_val_green
    ldr x3, =target_general
    mov x4, #len_target_general
    ldr x5, =risk_low
    mov x6, #len_risk_low
    ldr x7, =reason_normal
    mov x8, #len_reason_normal
    mov x19, #0
    mov x20, #0
    bl print_structured
    ldp x29, x30, [sp], #16
    ret

print_manual:
    ldr x1, =val_no_action
    mov x2, #len_val_no_action
    ldr x3, =target_general
    mov x4, #len_target_general
    ldr x5, =risk_low
    mov x6, #len_risk_low
    ldr x7, =reason_manual
    mov x8, #len_reason_manual
    mov x19, #0
    mov x20, #0
    bl print_structured
    b main_loop

print_startup:
    ldr x1, =val_no_action
    mov x2, #len_val_no_action
    ldr x3, =target_general
    mov x4, #len_target_general
    ldr x5, =risk_low
    mov x6, #len_risk_low
    ldr x7, =reason_startup
    mov x8, #len_reason_startup
    mov x19, #0
    mov x20, #0
    bl print_structured
    ldp x29, x30, [sp], #16
    ret


print_structured:
    // Pointers are passed via x1-x8:
    // x1, x2 = Action
    // x3, x4 = Target
    // x5, x6 = Risk
    // x7, x8 = Reason
    // x19 = Value
    // x20 = Indicator

    stp x29, x30, [sp, #-96]!
    mov x29, sp

    // Salvar registros que usaremos
    str x1, [sp, #16]
    str x2, [sp, #24]
    str x3, [sp, #32]
    str x4, [sp, #40]
    str x5, [sp, #48]
    str x6, [sp, #56]
    str x19, [sp, #64]
    str x20, [sp, #72]
    str x7, [sp, #80]
    str x8, [sp, #88]

    // ACTION=
    mov x0, #1
    ldr x1, =key_action
    mov x2, #len_key_action
    mov x8, #64
    svc #0

    ldr x1, [sp, #16]
    ldr x2, [sp, #24]
    mov x0, #1
    mov x8, #64
    svc #0

    // TARGET=
    mov x0, #1
    ldr x1, =key_target
    mov x2, #len_key_target
    mov x8, #64
    svc #0

    ldr x1, [sp, #32]
    ldr x2, [sp, #40]
    mov x0, #1
    mov x8, #64
    svc #0

    // RISK=
    mov x0, #1
    ldr x1, =key_risk
    mov x2, #len_key_risk
    mov x8, #64
    svc #0

    ldr x1, [sp, #48]
    ldr x2, [sp, #56]
    mov x0, #1
    mov x8, #64
    svc #0

    // REASON= (X7, X8 were saved on stack)
    ldr x21, [sp, #80]
    ldr x22, [sp, #88]

    mov x0, #1
    ldr x1, =key_reason
    mov x2, #len_key_reason
    mov x8, #64
    svc #0

    mov x0, #1
    mov x1, x21
    mov x2, x22
    mov x8, #64
    svc #0

    ldr x19, [sp, #64]
    ldr x20, [sp, #72]
    // VALUE=
    mov x0, #1
    ldr x1, =key_value
    mov x2, #len_key_value
    mov x8, #64
    svc #0

    mov x0, x19
    ldr x1, =num_buffer
    bl int_to_ascii_local

    mov x2, x0
    mov x0, #1
    ldr x1, =num_buffer
    mov x8, #64
    svc #0

    mov x0, #1
    ldr x1, =newline
    mov x2, #1
    mov x8, #64
    svc #0

    // INDICATOR=
    mov x0, #1
    ldr x1, =key_indicator
    mov x2, #len_key_indicator
    mov x8, #64
    svc #0

    mov x0, x20
    ldr x1, =num_buffer
    bl int_to_ascii_local

    mov x2, x0
    mov x0, #1
    ldr x1, =num_buffer
    mov x8, #64
    svc #0

    mov x0, #1
    ldr x1, =newline
    mov x2, #1
    mov x8, #64
    svc #0

    // STATUS=OK
    mov x0, #1
    ldr x1, =key_status
    mov x2, #len_key_status
    mov x8, #64
    svc #0

    ldp x29, x30, [sp], #96
    ret

print_error:
    mov x0, #1
    ldr x1, =err_input
    mov x2, #len_err_input
    mov x8, #64
    svc #0
    b main_loop