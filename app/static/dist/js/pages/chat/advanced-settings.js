// Advanced settings handling with jQuery

const AdvancedSettings = {
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
    $modelSelect: $("#modelSelect"), // ← NEW
  },

  init: function () {
    const self = this;

    // Toggle advanced settings panel
    this.elements.$toggleSettings.on("click", function () {
      self.elements.$settingsPanel.toggleClass("active");
    });

    // Temperature slider input
    this.elements.$temperatureSlider.on("input", function () {
      self.elements.$temperatureValue.text($(this).val());
    });

    // Creativity slider input
    this.elements.$creativitySlider.on("input", function () {
      self.elements.$creativityValue.text($(this).val());
    });

    // Context length slider input
    this.elements.$contextSlider.on("input", function () {
      self.elements.$contextValue.text($(this).val());
    });
  },

  getParameters: function () {
    return {
      temperature: parseFloat(this.elements.$temperatureSlider.val()),
      creativity: parseFloat(this.elements.$creativitySlider.val()),
      context_length: parseInt(this.elements.$contextSlider.val(), 10),
      custom_instructions: this.elements.$customInstructions.val().trim(),
      model: this.elements.modelSelect.value,
    };
  },
};

// Export the module
window.AdvancedSettings = AdvancedSettings;

// Initialize on document ready
$(function () {
  AdvancedSettings.init();
});
