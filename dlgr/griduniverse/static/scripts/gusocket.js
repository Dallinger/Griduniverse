/*jshint esversion: 6 */
/**
 * Wrapper around ReconnectingWebSocket
 */

import ReconnectingWebSocket from "reconnecting-websocket";

export class GUSocket {
  constructor(settings) {
    const tolerance =
      settings.lagTolerance === undefined ? 0.1 : settings.lagTolerance;
    this.globalBroadcastChannel = settings.broadcast;
    this.globalControlChannel = settings.control;
    this.callbackMap = settings.callbackMap;
    this.socket = this._makeSocket(
      settings.endpoint,
      this.globalBroadcastChannel,
      tolerance,
    );

    this.socket.onmessage = (event) => {
      this._globalDispatch(event);
    };
  }

  addGameChannels(broadcastChannel, controlChannel) {
    this.broadcastChannel = broadcastChannel;
    this.controlChannel = controlChannel;
    this.gameSocket = this._makeSocket(
      settings.endpoint,
      this.broadcastChannel,
      tolerance,
    );

    this.gameSocket.onmessage = (event) => {
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

  sendGlobal(data) {
    const msg = JSON.stringify(data);
    const channel = this.globalControlChannel;
    console.log(`Sending message to the ${channel} channel: ${msg}`);
    this.socket.send(`${channel}:${msg}`);
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

  _baseDispatch(event) {
    const msg = JSON.parse(event.data.substring(marker.length));
    const callback = this.callbackMap[msg.type];
    if (callback !== undefined) {
      callback(msg);
    } else {
      console.log(`Unrecognized message type ${msg.type} from backend.`);
    }
  }

  _globalDispatch(event) {
    const marker = `${this.globalBroadcastChannel}:`;
    if (!event.data.startsWith(marker)) {
      console.log(
        `Message was not on channel ${this.globalBroadcastChannel}. Ignoring.`,
      );
      return;
    }
    _baseDispatch(event);
  }

  _dispatch(event) {
    const marker = `${this.broadcastChannel}:`;
    if (!event.data.startsWith(marker)) {
      console.log(
        `Message was not on channel ${this.broadcastChannel}. Ignoring.`,
      );
      return;
    }
    _baseDispatch(event);
  }
}
