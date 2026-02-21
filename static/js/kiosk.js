/**
 * kiosk.js — Shared utilities for kiosk screens.
 *
 * Screen-specific Socket.IO logic lives in the inline <script> blocks of
 * each template.  This file handles global kiosk hardening.
 */

'use strict';

document.addEventListener('DOMContentLoaded', function () {
  if (!document.body.classList.contains('kiosk-screen')) return;

  // Disable right-click context menu
  document.addEventListener('contextmenu', function (e) {
    e.preventDefault();
  });

  // Prevent pinch-to-zoom on touch displays
  document.addEventListener('touchstart', function (e) {
    if (e.touches.length > 1) e.preventDefault();
  }, { passive: false });

  // Prevent double-tap zoom
  let lastTap = 0;
  document.addEventListener('touchend', function (e) {
    const now = Date.now();
    if (now - lastTap < 300) e.preventDefault();
    lastTap = now;
  }, { passive: false });
});
