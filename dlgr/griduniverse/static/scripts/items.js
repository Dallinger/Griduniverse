/**
 * Representation of a game item, which for the moment is limited to a
 * simple Food type.
 */

export class Item {
  constructor(id, itemId, maturity, remainingUses) {
    this.id = id;
    this.itemId = itemId;
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

/**
 * Manages Items that sit on the grid.
 *
 * Items currently being carried by a Player are not included.
 * These are instead held by reference in the Play instances,
 * (named `current_item`).
 */
export class GridItems {
  constructor() {
    this._itemsByPosition = new Map();
    this._positionsById = new Map();
  }

  add(item, position) {
    this._itemsByPosition.set(JSON.stringify(position), item);
    this._positionsById.set(item.id, JSON.stringify(position));
  }

  atPosition(position) {
    const key = JSON.stringify(position);
    return this._itemsByPosition.get(key);
  }

  positionOf(item) {
    return JSON.parse(this._positionsById.get(item.id));
  }

  remove(item) {
    this._itemsByPosition.delete(JSON.stringify(item.position));
    this._positionsById.delete(item.id);
  }

  /**
   * Retrieve pairs of positions and Item objects (like Python's dict.items())
   * @returns Map.prototype[@@iterator] of[position, Item] pairs
   */
  *entries() {
    for (const [itemPosition, currentItem] of this._itemsByPosition.entries()) {
      yield [JSON.parse(itemPosition), currentItem];
    }
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
