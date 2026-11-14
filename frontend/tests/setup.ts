import '@testing-library/jest-dom/vitest'
import { configure } from '@testing-library/react'

configure({ asyncUtilTimeout: 8000 })

// jsdom lacks <dialog>.showModal/close — minimal polyfill for tests
if (typeof HTMLDialogElement !== 'undefined' && !HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true
  }
  HTMLDialogElement.prototype.close = function () {
    this.open = false
    this.dispatchEvent(new Event('close'))
  }
}
