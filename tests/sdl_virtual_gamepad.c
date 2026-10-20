/* Test-only in-process SDL virtual gamepad. Never creates kernel input devices. */
#include <SDL3/SDL.h>
#include <stddef.h>

static SDL_Joystick *joystick;

SDL_JoystickID test_attach(void)
{
    SDL_VirtualJoystickDesc desc;
    SDL_INIT_INTERFACE(&desc);
    desc.type = SDL_JOYSTICK_TYPE_GAMEPAD;
    desc.vendor_id = 0x1234;
    desc.product_id = 0x5678;
    desc.naxes = SDL_GAMEPAD_AXIS_COUNT;
    desc.nbuttons = SDL_GAMEPAD_BUTTON_COUNT;
    desc.axis_mask = (1u << SDL_GAMEPAD_AXIS_COUNT) - 1;
    desc.button_mask = (1u << SDL_GAMEPAD_BUTTON_COUNT) - 1;
    desc.name = "Decktation synthetic SDL fixture";
    SDL_JoystickID id = SDL_AttachVirtualJoystick(&desc);
    if (!id) return 0;
    joystick = SDL_OpenJoystick(id);
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_LEFT_TRIGGER, -32768);
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER, -32768);
    SDL_UpdateJoysticks();
    return id;
}

bool test_button(int index, bool down)
{
    bool result = SDL_SetJoystickVirtualButton(joystick, index, down);
    SDL_UpdateJoysticks();
    return result;
}

bool test_axis(int index, int value)
{
    bool result = SDL_SetJoystickVirtualAxis(joystick, index, (Sint16)value);
    SDL_UpdateJoysticks();
    return result;
}

bool test_detach(SDL_JoystickID id)
{
    bool result = SDL_DetachVirtualJoystick(id);
    SDL_CloseJoystick(joystick);
    joystick = NULL;
    return result;
}

int test_event_size(void) { return sizeof(SDL_Event); }
int test_button_offset(void) { return offsetof(SDL_GamepadButtonEvent, button); }
int test_axis_value_offset(void) { return offsetof(SDL_GamepadAxisEvent, value); }
