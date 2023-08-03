/**
 * Representation of a game item, which for the moment is limited to a
 * simple Food type.
 */

export class Item {
  constructor(id, itemId, position, maturity, remainingUses) {
    this.id = id;
    this.itemId = itemId;
    this.position = position;
    this.maturity = maturity;
    this.remainingUses = remainingUses;
    // XXX Maybe we can avoid this copy of every shared value
    // to every instance, but going with it for now.
    Object.assign(this, settings.item_config[this.itemId]);
  }

  /**
   * Calculate a color based on sprite definition and maturity
   */
  get color() {
    let immature, mature;

    if (this.sprite.includes(",")) {
      [immature, mature] = this.sprite.split(",");
      // For now, assume these are hex colors
    } else {
      immature = mature = this.sprite;
    }

    return rgbOnScale(
      hexToRgbPercentages(immature),
      hexToRgbPercentages(mature),
      this.maturity
    );
  }
}

export class GridItems {
  constructor() {
    this._itemsByPosition = new Map();
  }

  add(item) {
    this._itemsByPosition.set(JSON.stringify(item.position), item);
  }

  atPosition(position) {
    const key = JSON.stringify(position);
    return this._itemsByPosition.get(key);
  }

  remove(item) {
    this._itemsByPosition.delete(JSON.stringify(item.position));
    item.position = null;
  }
  /**
   * Retrieve the Item values from the GridItems
   * @returns Map.prototype[@@iterator]
   */
  values() {
    return this._itemsByPosition.values();
  }
}

function hexToRgbPercentages(hexColor) {
  if (hexColor.startsWith("#")) {
    hexColor = hexColor.substring(1);
  }

  // Check if the hex color has a valid length (either 3 or 6 characters)
  if (hexColor.length !== 3 && hexColor.length !== 6) {
    throw new Error(
      "Invalid hex color format. It should be either 3 or 6 characters long."
    );
  }

  // If the hex color is 3 characters long, expand it to 6 characters by
  // duplicating each character
  if (hexColor.length === 3) {
    hexColor = hexColor
      .split("")
      .map((char) => char + char)
      .join("");
  }

  // Convert the hex color to RGB percentage values
  const red = parseInt(hexColor.substring(0, 2), 16) / 255;
  const green = parseInt(hexColor.substring(2, 4), 16) / 255;
  const blue = parseInt(hexColor.substring(4, 6), 16) / 255;

  return [red, green, blue];
}

function rgbOnScale(startColor, endColor, percentage) {
  const result = [];
  for (let i = 0; i < 3; i++) {
    result[i] = endColor[i] + percentage * (startColor[i] - endColor[i]);
  }

  return result;
}
