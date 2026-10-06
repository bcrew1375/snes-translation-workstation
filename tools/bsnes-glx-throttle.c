#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdlib.h>
#include <time.h>

#include <GL/glx.h>

/*
 * Xvfb has no physical vertical blank, so bsnes-plus' GLX synchronization does
 * not limit emulation speed.  Pace completed frame swaps against a monotonic
 * clock instead.  The rate can be overridden for PAL or deliberate speed-up.
 */

typedef void (*SwapBuffers)(Display *, GLXDrawable);

static SwapBuffers real_swap_buffers;
static pthread_mutex_t throttle_lock = PTHREAD_MUTEX_INITIALIZER;
static struct timespec deadline;
static long period_ns;
static int initialized;

static long long timespec_ns(struct timespec value) {
  return (long long)value.tv_sec * 1000000000LL + value.tv_nsec;
}

static struct timespec ns_timespec(long long value) {
  struct timespec result = {
    .tv_sec = value / 1000000000LL,
    .tv_nsec = value % 1000000000LL,
  };
  return result;
}

void glXSwapBuffers(Display *display, GLXDrawable drawable) {
  if (!real_swap_buffers) {
    real_swap_buffers = (SwapBuffers)dlsym(RTLD_NEXT, "glXSwapBuffers");
  }
  real_swap_buffers(display, drawable);

  pthread_mutex_lock(&throttle_lock);
  struct timespec now;
  clock_gettime(CLOCK_MONOTONIC, &now);
  if (!initialized) {
    const char *value = getenv("BSNES_FRAME_HZ");
    double hz = value ? strtod(value, NULL) : 60.0988;
    if (hz < 1.0 || hz > 1000.0) hz = 60.0988;
    period_ns = (long)(1000000000.0 / hz);
    deadline = ns_timespec(timespec_ns(now) + period_ns);
    initialized = 1;
  } else {
    long long next = timespec_ns(deadline) + period_ns;
    long long current = timespec_ns(now);
    if (current - next > period_ns * 4LL) next = current + period_ns;
    deadline = ns_timespec(next);
  }
  struct timespec target = deadline;
  pthread_mutex_unlock(&throttle_lock);

  while (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &target, NULL) == EINTR) {
  }
}