/*jshint esversion: 6 */
/**
 * Wrapper around ReconnectingWebSocket
 */

import ReconnectingWebSocket from "reconnecting-websocket";

export class GUSocket {
  constructor(settings) {
    if (!(this instanceof GUSocket)) {
      return new GUSocket(settings);
    }

    const tolerance =
      settings.lagTolerance === undefined ? 0.1 : settings.lagTolerance;

    this.broadcastChannel = settings.broadcast;
    this.controlChannel = settings.control;
    this.callbackMap = settings.callbackMap;
    this.socket = this._makeSocket(
      settings.endpoint,
      this.broadcastChannel,
      tolerance,
    );

    this.socket.onmessage = (event) => {
      this._dispatch(event);
    };
  }

  open() {
    const isOpen = $.Deferred();
    this.socket.onopen = () => {
      isOpen.resolve();
    };

    return isOpen;
  }

  send(data) {
    const msg = JSON.stringify(data);
    const channel = this.controlChannel;
    console.log(`Sending message to the ${channel} channel: ${msg}`);
    this.socket.send(`${channel}:${msg}`);
  }

  broadcast(data) {
    const msg = JSON.stringify(data);
    const channel = this.broadcastChannel;
    console.log(`Broadcasting message to the ${channel} channel: ${msg}`);
    this.socket.send(`${channel}:${msg}`);
  }

  _makeSocket(endpoint, channel, tolerance) {
    const ws_scheme =
      window.location.protocol === "https:" ? "wss://" : "ws://";
    const app_root = `${ws_scheme}${location.host}/`;
    const socketUrl = `${app_root}${endpoint}?channel=${channel}&tolerance=${tolerance}`;
    const socket = new ReconnectingWebSocket(socketUrl);
    socket.debug = true;

    return socket;
  }

  _dispatch(event) {
    const marker = `${this.broadcastChannel}:`;
    if (!event.data.startsWith(marker)) {
      console.log(
        `Message was not on channel ${this.broadcastChannel}. Ignoring.`,
      );
      return;
    }
    const msg = JSON.parse(event.data.substring(marker.length));
    const callback = this.callbackMap[msg.type];
    if (callback !== undefined) {
      callback(msg);
    } else {
      console.log(`Unrecognized message type ${msg.type} from backend.`);
    }
  }
}
