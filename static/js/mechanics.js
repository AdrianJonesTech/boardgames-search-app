let selectedMechanics = new Set();  // Will be initialized from template data

function updateSelectedBadges() {
    const badgesContainer = document.getElementById('selectedBadges');
    const countSpan = document.getElementById('selectedCount');
    const clearBtn = document.getElementById('clearAllBtn');
    const hiddenSelect = document.querySelector('select[name="mechanics"]');  // Hardcoded name for static JS

    badgesContainer.innerHTML = '';
    selectedMechanics.forEach(id => {
        const optionItem = Array.from(document.querySelectorAll('.option-item')).find(item => item.dataset.id === id.toString());
        const name = optionItem ? optionItem.dataset.name : id;  // Fallback to ID if name not found
        const badge = document.createElement('span');
        badge.className = 'badge bg-primary text-wrap';
        badge.style.cursor = 'pointer';
        badge.innerHTML = `${name} <span class="ms-1" onclick="removeMechanic('${id}')" style="cursor: pointer; font-weight: bold;">&times;</span>`;
        badgesContainer.appendChild(badge);
    });

    const count = selectedMechanics.size;
    countSpan.textContent = `Select mechanisms (${count} selected)`;
    clearBtn.style.display = count > 0 ? 'inline-block' : 'none';

    // Update hidden select
    if (hiddenSelect) {
        Array.from(hiddenSelect.options).forEach(option => {
            option.selected = selectedMechanics.has(option.value);
        });
    }

    // Trigger HTMX change
    if (hiddenSelect) {
        hiddenSelect.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

function addMechanic(id, name) {
    selectedMechanics.add(id);
    updateSelectedBadges();
}

window.removeMechanic = function(id) {
    selectedMechanics.delete(id);
    updateSelectedBadges();
};

window.clearMechanics = function() {
    selectedMechanics.clear();
    updateSelectedBadges();
};

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize selectedMechanics from hidden select (more robust than template var)
    const hiddenSelect = document.querySelector('select[name="mechanics"]');
    if (hiddenSelect) {
        Array.from(hiddenSelect.options).forEach(option => {
            if (option.selected) {
                selectedMechanics.add(option.value);
            }
        });
    }
    updateSelectedBadges();  // Initial render

    document.querySelectorAll('.option-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const id = this.dataset.id;
            if (selectedMechanics.has(id)) {
                removeMechanic(id);
            } else {
                addMechanic(id, this.dataset.name);
            }
            // Close dropdown after selection
            const dropdownElement = document.getElementById('mechanicsDropdown');
            const dropdown = bootstrap.Dropdown.getInstance(dropdownElement);
            if (dropdown) dropdown.hide();
        });
    });
});