/* Experimental Gamescope text injector. Protocol pinned in the adjacent XML.
 * Reads one complete UTF-8 message from stdin; never accepts text on argv.
 * Exit 0 confirms compositor roundtrip, NOT that a game displayed the text.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <wayland-client.h>
#include "gamescope-input-method-client-protocol.h"

#define MAX_TEXT_BYTES 160
#define MAX_TEXT_CHARS 40 /* Gamescope has 47 simultaneous keycode slots. */

struct context {
    struct wl_seat *seat;
    struct gamescope_input_method_manager *manager;
    uint32_t serial;
    bool done;
    bool unavailable;
};

static void registry_global(void *data, struct wl_registry *registry, uint32_t name,
                            const char *interface, uint32_t version)
{
    struct context *ctx = data;
    if (!strcmp(interface, wl_seat_interface.name) && !ctx->seat)
        ctx->seat = wl_registry_bind(registry, name, &wl_seat_interface, 1);
    else if (!strcmp(interface, gamescope_input_method_manager_interface.name) && !ctx->manager)
        ctx->manager = wl_registry_bind(registry, name, &gamescope_input_method_manager_interface,
                                        version < 3 ? version : 3);
}
static void registry_removed(void *data, struct wl_registry *registry, uint32_t name)
{
    (void)data; (void)registry; (void)name;
}
static const struct wl_registry_listener registry_listener = {registry_global, registry_removed};

static void ime_done(void *data, struct gamescope_input_method *ime, uint32_t serial)
{
    (void)ime;
    struct context *ctx = data;
    ctx->serial = serial;
    ctx->done = true;
}
static void ime_unavailable(void *data, struct gamescope_input_method *ime)
{
    (void)ime;
    ((struct context *)data)->unavailable = true;
}
static const struct gamescope_input_method_listener ime_listener = {
    .unavailable = ime_unavailable, .done = ime_done
};

static bool continuation(unsigned char b) { return (b & 0xc0) == 0x80; }

static bool valid_text(const unsigned char *text, size_t length)
{
    if (!length || length > MAX_TEXT_BYTES) return false;
    size_t characters = 0;
    for (size_t i = 0; i < length;) {
        if (++characters > MAX_TEXT_CHARS) return false;
        unsigned char c = text[i++];
        if (c >= 0x20 && c <= 0x7e) continue;
        if (c >= 0xc2 && c <= 0xdf) {
            if (i >= length || !continuation(text[i])) return false;
            i++;
        } else if (c >= 0xe0 && c <= 0xef) {
            if (i + 1 >= length || !continuation(text[i + 1])) return false;
            unsigned char b = text[i];
            if ((c == 0xe0 && b < 0xa0) || (c == 0xed && b >= 0xa0) || !continuation(b)) return false;
            i += 2;
        } else if (c >= 0xf0 && c <= 0xf4) {
            if (i + 2 >= length || !continuation(text[i + 1]) || !continuation(text[i + 2])) return false;
            unsigned char b = text[i];
            if ((c == 0xf0 && b < 0x90) || (c == 0xf4 && b > 0x8f) || !continuation(b)) return false;
            i += 3;
        } else return false;
    }
    return true;
}

int main(int argc, char **argv)
{
    bool probe = argc == 2 && !strcmp(argv[1], "--probe");
    if (!(argc == 1 || probe)) return 2;
    unsigned char text[MAX_TEXT_BYTES + 2] = {0};
    if (!probe) {
        size_t length = fread(text, 1, MAX_TEXT_BYTES + 1, stdin);
        if (ferror(stdin) || length > MAX_TEXT_BYTES) {
            fprintf(stderr, "Invalid text\n");
            return 2;
        }
        if (!valid_text(text, length)) {
            fprintf(stderr, "Invalid text\n");
            return 2;
        }
        text[length] = '\0';
    }

    const char *display_name = getenv("GAMESCOPE_WAYLAND_DISPLAY");
    if (!display_name || !*display_name) display_name = "gamescope-0";
    struct wl_display *display = wl_display_connect(display_name);
    if (!display) { fprintf(stderr, "Gamescope socket unavailable\n"); return 1; }
    struct context ctx = {0};
    struct wl_registry *registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, &ctx);
    int status = 1;
    struct gamescope_input_method *ime = NULL;
    if (wl_display_roundtrip(display) < 0 || !ctx.seat || !ctx.manager) {
        fprintf(stderr, "Gamescope input method or seat unavailable\n");
        goto cleanup;
    }
    if (probe) { status = 0; goto cleanup; }
    ime = gamescope_input_method_manager_create_input_method(ctx.manager, ctx.seat);
    if (!ime) { fprintf(stderr, "Gamescope input method unavailable\n"); goto cleanup; }
    gamescope_input_method_add_listener(ime, &ime_listener, &ctx);
    if (wl_display_roundtrip(display) < 0 || ctx.unavailable || !ctx.done) {
        fprintf(stderr, "Gamescope input method unavailable\n");
        goto cleanup;
    }
    gamescope_input_method_set_string(ime, (const char *)text);
    gamescope_input_method_commit(ime, ctx.serial);
    if (wl_display_roundtrip(display) < 0 || ctx.unavailable) {
        fprintf(stderr, "Gamescope commit failed\n");
        goto cleanup;
    }
    /* Gamescope keeps its temporary keymap for 100 ms after commit; keep the
     * IME resource alive longer so clients can interpret the queued keycodes.
     * This is still not an acknowledgement from the focused game. */
    struct timespec drain = {.tv_sec = 0, .tv_nsec = 150000000L};
    while (nanosleep(&drain, &drain) < 0 && errno == EINTR) {}
    status = 0;
cleanup:
    if (ime) gamescope_input_method_destroy(ime);
    if (ctx.manager) gamescope_input_method_manager_destroy(ctx.manager);
    if (ctx.seat) wl_seat_destroy(ctx.seat);
    wl_registry_destroy(registry);
    wl_display_disconnect(display);
    return status;
}
