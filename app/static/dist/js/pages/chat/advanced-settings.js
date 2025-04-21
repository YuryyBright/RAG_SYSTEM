// Advanced settings handling

const AdvancedSettings = {
  // DOM Elements
  elements: {
    toggleSettings: document.getElementById("toggleAdvancedSettings"),
    settingsPanel: document.getElementById("advancedSettings"),
    temperatureSlider: document.getElementById("temperatureSlider"),
    temperatureValue: document.getElementById("temperatureValue"),
    creativitySlider: document.getElementById("creativitySlider"),
    creativityValue: document.getElementById("creativityValue"),
    contextSlider: document.getElementById("contextSlider"),
    contextValue: document.getElementById("contextValue"),
    customInstructions: document.getElementById("customInstructions"),
  },

  // Initialize event handlers
  init() {
    // Toggle advanced settings panel
    this.elements.toggleSettings.addEventListener("click", () => {
      this.elements.settingsPanel.classList.toggle("active");
    });

    // Temperature slider
    this.elements.temperatureSlider.addEventListener("input", (e) => {
      this.elements.temperatureValue.textContent = e.target.value;
    });

    // Creativity slider
    this.elements.creativitySlider.addEventListener("input", (e) => {
      this.elements.creativityValue.textContent = e.target.value;
    });

    // Context length slider
    this.elements.contextSlider.addEventListener("input", (e) => {
      this.elements.contextValue.textContent = e.target.value;
    });
  },

  // Get all current parameter values
  getParameters() {
    return {
      temperature: parseFloat(this.elements.temperatureSlider.value),
      creativity: parseFloat(this.elements.creativitySlider.value),
      context_length: parseInt(this.elements.contextSlider.value),
      custom_instructions: this.elements.customInstructions.value.trim(),
    };
  },
};

// Export the module
window.AdvancedSettings = AdvancedSettings;
