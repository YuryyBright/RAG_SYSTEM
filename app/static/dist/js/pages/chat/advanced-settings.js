// =====================================================================
// advanced-settings.js - IMPROVED VERSION
// =====================================================================

export const AdvancedSettings = {
  elements: {
    $toggleSettings: $("#toggleAdvancedSettings"),
    $settingsPanel: $("#advancedSettings"),
    $temperatureSlider: $("#temperatureSlider"),
    $temperatureValue: $("#temperatureValue"),
    $creativitySlider: $("#creativitySlider"),
    $creativityValue: $("#creativityValue"),
    $contextSlider: $("#contextSlider"),
    $contextValue: $("#contextValue"),
    $customInstructions: $("#customInstructions"),
    // Model selection handled in the sidebar
  },

  init: function () {
    // Re-initialize element references
    this.elements = {
      $toggleSettings: $("#toggleAdvancedSettings"),
      $settingsPanel: $("#advancedSettings"),
      $temperatureSlider: $("#temperatureSlider"),
      $temperatureValue: $("#temperatureValue"),
      $creativitySlider: $("#creativitySlider"),
      $creativityValue: $("#creativityValue"),
      $contextSlider: $("#contextSlider"),
      $contextValue: $("#contextValue"),
      $customInstructions: $("#customInstructions"),
    };

    const self = this;

    // Toggle advanced settings panel
    this.elements.$toggleSettings.off("click").on("click", function () {
      self.elements.$settingsPanel.toggleClass("active");

      // Update button text
      const isActive = self.elements.$settingsPanel.hasClass("active");
      $(this).html(
        isActive ? '<i class="fas fa-cog fa-spin"></i> Hide Advanced' : '<i class="fas fa-cog"></i> Advanced Settings'
      );
    });

    // Temperature slider input
    this.elements.$temperatureSlider.off("input").on("input", function () {
      const value = parseFloat($(this).val()).toFixed(2);
      self.elements.$temperatureValue.text(value);
    });

    // Set initial value for temperature
    if (this.elements.$temperatureSlider.length && this.elements.$temperatureValue.length) {
      this.elements.$temperatureValue.text(parseFloat(this.elements.$temperatureSlider.val()).toFixed(2));
    }

    // Creativity slider input
    this.elements.$creativitySlider.off("input").on("input", function () {
      const value = parseFloat($(this).val()).toFixed(2);
      self.elements.$creativityValue.text(value);
    });

    // Set initial value for creativity
    if (this.elements.$creativitySlider.length && this.elements.$creativityValue.length) {
      this.elements.$creativityValue.text(parseFloat(this.elements.$creativitySlider.val()).toFixed(2));
    }

    // Context length slider input
    this.elements.$contextSlider.off("input").on("input", function () {
      const value = parseInt($(this).val(), 10);
      self.elements.$contextValue.text(value);
    });

    // Set initial value for context length
    if (this.elements.$contextSlider.length && this.elements.$contextValue.length) {
      this.elements.$contextValue.text(parseInt(this.elements.$contextSlider.val(), 10));
    }
  },

  getParameters: function () {
    const params = {};

    // Add parameters only if elements exist
    if (this.elements.$temperatureSlider.length) {
      params.temperature = parseFloat(this.elements.$temperatureSlider.val());
    }

    if (this.elements.$creativitySlider.length) {
      params.creativity = parseFloat(this.elements.$creativitySlider.val());
    }

    if (this.elements.$contextSlider.length) {
      params.context_length = parseInt(this.elements.$contextSlider.val(), 10);
    }

    if (this.elements.$customInstructions.length) {
      const instructions = this.elements.$customInstructions.val()?.trim();
      if (instructions) {
        params.custom_instructions = instructions;
      }
    }

    return params;
  },
};
